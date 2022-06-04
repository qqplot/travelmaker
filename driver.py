from neo4j import GraphDatabase
from google.cloud import bigquery
from google.oauth2 import service_account
from collections import deque
import random
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

        new_days = "2" if days == "2" else "4"
        query_string = '''
            MATCH p=(c1:city{city_id:"%s"})-[rels:goes*1..%s]->(c2:city{city_id:"%s"})
            WHERE rels[0].depart_time < time('%s') and reduce(total=0, r in rels | total+r.dist)<400
            RETURN nodes(p) as node,relationships(p) as rels
            limit 500
            '''%(city_id_from, new_days, city_id_to, depart_time)
        q = conn.query(query_string, db='traveldb')
        result_list=deque()
        result_list.append(0)
        tmp_result=deque()
        past_result=deque()

        for _ in q:
            city_set=set()
            for i in range(len(dict(_)['node'])):
                if i != len(dict(_)['node'])-1 and not dict(dict(dict(_))['node'][i])['city_nm'] in city_set:
                    city_set.add(dict(dict(dict(_))['node'][i])['city_nm'])
                    tmp_result.append((dict(dict(dict(_))['node'][i])['city_nm'],
                dict(dict(dict(_))['node'][i])['city_id'],
                dict(dict(dict(_))['node'][i])['latitude'],
                dict(dict(dict(_))['node'][i])['longitude'],
                dict(dict(dict(_))['rels'][i])['trans_cate']))
                else:
                    tmp_result.append((dict(dict(dict(_))['node'][i])['city_nm'],
                dict(dict(dict(_))['node'][i])['city_id'],                
                dict(dict(dict(_))['node'][i])['latitude'],
                dict(dict(dict(_))['node'][i])['longitude'],
                                      0))
            if  len(dict(_)['node'])==len(tmp_result) and not past_result == tmp_result:
                result_list.append(tuple(tmp_result))
            past_result=tmp_result
            tmp_result=list()
        result_list.popleft()
        result_list=list(result_list)
        result_list=list(dict.fromkeys(result_list))

        MAX_LEN = 10
        result_list_shuffle = [None] * MAX_LEN
        
        if len(result_list) < MAX_LEN: 
            return result_list
        else:
            tmp_list=list(range(len(result_list)))
            tmp_list=random.sample(tmp_list,MAX_LEN)
            for i in range(MAX_LEN):
                result_list_shuffle[i]=result_list[tmp_list[i]]
            
            return result_list_shuffle


    
    
    def get_unique_city(paths):
        
        cities = set()
        result = []
        for path in paths:
            for p in path:
                if not p[0] in cities:
                    cities.add(p[0])
                    result.append(p)

        return result


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


    def recommend(client, city_id, x, y, theme, city_name):
        sql = """
        WITH accommodation AS(
              select city_id, accom_nm, rate, longitude, latitude, 
              round(st_distance(st_geogpoint({}, {}), st_geogpoint(longitude, latitude)),2) as distance
              from `travel-maker-352004.tour.accomodation`
              where city_id = '{}'
              AND rate > 4.0
              ORDER BY rate DESC, distance
              LIMIT 5),
        attraction AS(
              select city_id, attraction_nm, rate, longitude, latitude
                from `travel-maker-352004.tour.attraction`
              where city_id = '{}' and theme = '{}' and rate > 4.0
              order by rand()
              limit 2),
        avg_dist AS (
              select city_id, avg(longitude) as avglong, avg(latitude) as avglat
              from attraction
              group by city_id
        ),
        restaurant_dist AS(
              select r.city_id, r.rest_id, r.rest_nm, r.rest_cat, r.rate, r.longitude, r.latitude,
                cast(st_distance(st_geogpoint(a.avglong, a.avglat), st_geogpoint(r.longitude, r.latitude)) as int64)as distance
              from `travel-maker-352004.tour.restaurants` r
              JOIN avg_dist a
              ON r.city_id = a.city_id 
              where r.city_id = '{}'
        ),
        row_num_add AS(
              SELECT *, ROW_NUMBER() OVER(PARTITION BY rest_cat ORDER BY distance) AS row_number
              FROM restaurant_dist
              WHERE distance >= 1.0 AND rate > 4.5
        ),
        restaurant AS(
              SELECT city_id, rest_cat, rest_nm, rate, distance, longitude, latitude
              from row_num_add
              where row_number=1
        )
        SELECT tmp1.city_id, 
               tmp1.accom_nm, 
               tmp1.rate as AccomRate, 
               tmp1.distance as AccomDist, 
               tmp1.longitude as AccomX, 
               tmp1.latitude as AccomY,
               tmp2.rest_cat, 
               tmp2.rest_nm, 
               tmp2.rate as RestRate, 
               tmp2.distance as RestDist, 
               tmp2.longitude as RestX, 
               tmp2.latitude as RestY,
               tmp3.attraction_nm, 
               tmp3.longitude as AttX, 
               tmp3.latitude as AttY
          from accommodation as tmp1
          join restaurant as tmp2 on tmp1.city_id = tmp2.city_id
          join (select city_id, attraction_nm, longitude, latitude
                  from attraction) as tmp3
               on tmp2.city_id = tmp3.city_id
        """.format(x, y, city_id, city_id, theme, city_id)

        query_job = client.query_gcp(sql)
        df = query_job.to_dataframe()

        attractions = set()
        restaurants = set()
        accomodations = set()

        for _, row in df.iterrows():
            accomodations.add((row['accom_nm'], round(row['AccomRate'], 2), row['AccomDist'], row['AccomX'], row['AccomY']))
            restaurants.add((row['rest_cat'], row['rest_nm'], round(row['RestRate'],2), row['RestDist'], row['RestX'], row['RestY']))
            attractions.add((row['city_id'], row['attraction_nm'], row['AttX'], row['AttY']))


        result = {
            'city_name' : city_name,
            'attractions' : list(attractions),
            'restaurants' : list(restaurants),
            'accomodations' : list(accomodations),
            'longitude' : x,
            'latitude' : y,
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


    
