from neo4j import GraphDatabase
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

class Neo4jConnection:
    
    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the driver:", e)
        
    def close(self):
        if self.__driver is not None:
            self.__driver.close()
        
    def query(self, query, db=None):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try: 
            session = self.__driver.session(database=db) if db is not None else self.__driver.session() 
            response = list(session.run(query))
        except Exception as e:
            print("Query failed:", e)
        finally: 
            if session is not None:
                session.close()
        return response

    def getPaths(conn, city_id_from, city_id_to, depart_time, days):

        new_days = "2" if days == "2" else "3"
    
       query_string = '''
            MATCH p=(c1:city{city_id:"%s"})-[rels:goes*1..%s]->(c2:city{city_id:"%s"})
            WHERE rels[0].depart_time < time('%s') and reduce(total=0, r in rels | total+r.fare)<40000
            RETURN nodes(p) as node,relationships(p) as rels
            limit 1000
            '''%(city_id_from, new_days, city_id_to, depart_time)
        q = conn.query(query_string, db='neo4j')
        result_list=[None]
        city_list=set() # prevent dupliactes
        tmp_result=list()
        past_result=list()
        print("query processed")
        for _ in q:
            for i in range(len(dict(_)['node'])):
                if i != len(dict(_)['node'])-1:
                    tmp_result.append((dict(dict(dict(_))['node'][i])['city_nm'],
                dict(dict(dict(_))['node'][i])['city_id'],
                dict(dict(dict(_))['rels'][i])['trans_cate']))
                else:
                    tmp_result.append((dict(dict(dict(_))['node'][i])['city_nm'],
                dict(dict(dict(_))['node'][i])['city_id'],
                                      0))
            if  not past_result == tmp_result:
                result_list.append(tuple(tmp_result))
            past_result=tmp_result
            tmp_result=list()
        del result_list[0]
        print(result_list)
        result_tuple=set(tuple(result_list))
        print(result_tuple)
    
    def get_unique_city(paths):
        
        cities = set()
        for path in paths:
            for p in path:
                cities.add(p);
        return cities


class GoogleBigQueryConnection:

    def __init__(self):
        self.credentials = service_account.Credentials.from_service_account_file('travel-maker-352004-8f65db2188bd.json')
        self.project_id = 'travel-maker-352004'
        try:
            self.__driver = bigquery.Client(credentials=self.credentials, project=self.project_id)
        except Exception as e:
            print("Failed to create the driver:", e)

    def close(self):
        if self.__driver is not None:
            self.__driver.close()

    def query_gcp(self, sql):
        assert self.__driver is not None, "Driver not initialized!"

        response = None
        try: 
            response = self.__driver.query(sql)
        except Exception as e:
            print("Query failed:", e)

        return response


    def selectAttraction(conn, city_id, theme):
    
        sql = """
        select city_id, attraction_nm, longitude, latitude 
        FROM `travel-maker-352004.tour.attraction` 
        where city_id = '{}' and theme = '{}'
        and  rate > 4.0
        order by rand() desc limit 2
        """.format(city_id, theme)

        query_job = conn.query_gcp(sql)
        
        df = query_job.to_dataframe()

        attractions = []
        for _, row in df.iterrows():
            attractions.append((row['city_id'], row['attraction_nm'], row['longitude'], row['latitude']))
      
        return attractions

    def selectRestaurant(conn, city_id, longitude, latitude):

        # 뽑은 attraction의 위도/경도, city id 입력하면 
        # 해당 attraction에서 가장 가까운 카테고리별 음식점 선별해줌. (rate 4.5이상)
    
        sql = """
        WITH restaurant_dist AS(
        select rest_id, rest_nm, rest_cat, rate,
            st_distance(st_geogpoint({}, {}), st_geogpoint(longitude, latitude)) as distance
        from `travel-maker-352004.tour.restaurants`
        where city_id = '{}')
        SELECT d.rest_cat, d.rest_nm, d.rate, d.distance
        FROM restaurant_dist d
        WHERE d.distance in
        (SELECT min(d.distance)
        FROM restaurant_dist d
        where d.distance != 0 and d.rate > 4.5
        group by d.rest_cat)
        LIMIT 10
        """.format(longitude, latitude, city_id)

        query_job = conn.query_gcp(sql)
        df = query_job.to_dataframe()

        restaurants = []
        for _, row in df.iterrows():
            restaurants.append((row['rest_cat'], row['rest_nm'], row['rate'], row['distance']))
        
        return restaurants

    def selectAccomodation(conn, city_id, longitude, latitude):

        # city의 위도/경도 및 city id 입력하면 
        # 해당 city역에서 평점 높고 거리 가까운 숙소 5개 뽑아줌 (평점 4.0이상)

        sql = """
            WITH accomodation_dist AS(
                select accom_nm, rate,
                    st_distance(st_geogpoint({}, {}), st_geogpoint(longitude, latitude))as distance
                from `tour.accomodation`
                where city_id = '{}')
            SELECT d.accom_nm, d.rate, d.distance
            FROM accomodation_dist d
            WHERE d.rate > 4.0
            ORDER BY d.rate DESC, d.distance
            LIMIT 5
            """.format(longitude, latitude, city_id)

        query_job = conn.query_gcp(sql)
        df = query_job.to_dataframe()

        accomodations = []
        for _, row in df.iterrows():
            accomodations.append((row['accom_nm'], row['rate'], row['distance']))
        
        return accomodations

    def recommend(conn, city_id, city_name, theme, longitude, latitude):

        attractions = GoogleBigQueryConnection.selectAttraction(conn, city_id, theme)
        restaurants = []
        # restaurants = GoogleBigQueryConnection.selectRestaurant(conn, city_id, longitude, latitude)
        for att in attractions:
            c_id, c_name, x, y = att
            restaurants.extend(GoogleBigQueryConnection.selectRestaurant(conn, city_id, x, y))
            break

        accomodations = GoogleBigQueryConnection.selectAccomodation(conn, city_id, longitude, latitude)

        result = {
            'city_name' : city_name,
            'attractions' : attractions,
            'restaurants' : restaurants,
            'accomodations' : accomodations,
            'longitude' : longitude,
            'latitude' : latitude,
        }

        return city_id, result

    

if __name__ == "__main__":
    conn = GoogleBigQueryConnection()
    city_id_from = "C01"
    city_id_to = "C05"
    depart_time = "13:00"
    days = "2"
    theme = 'Nature'
    longitude = "128.6287755"
    latitude = "35.87943614"

    city_id, result = GoogleBigQueryConnection.recommend(conn, city_id_to, theme, longitude, latitude)

    print(result)

    conn.close()


    
