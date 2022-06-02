from neo4j import GraphDatabase

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

if __name__ == "__main__":
    conn = Neo4jConnection(uri="bolt://localhost:7687", user="neo4j", pwd="0097")
    city_id_from = "C01"
    city_id_to = "C22"
    depart_time = "13:00"
    days = "2"
    query_string = '''
        MATCH p=(:city{city_id:"%s"})-[rels:goes*1..%s]->(:city{city_id:"%s"})
        WHERE rels[0].depart_time < time('%s')
        WITH nodes(p) as cities, p
        RETURN DISTINCT cities
        '''%(city_id_from, days, city_id_to, depart_time)
    q = conn.query(query_string, db='traveldb')

    result=list() # 바깥 리스트
    for _ in q:
        tmp_result=list() # 안쪽 리스트
        for j in range(len(dict(_)['cities'])):
            tmp_result.append((dict(dict(_)['cities'][j])['city_nm'],
                               dict(dict(_)['cities'][j])['city_id'],
                               dict(dict(_)['cities'][j])['latitude'],
                               dict(dict(_)['cities'][j])['longitude'] )) # 요소별 삽입 (컬럼명 주의)
        result.append(tmp_result) # path list를 바깥 리스트에 삽입
        print(result)
    conn.close()
    
    conn.close()

    
