
# Travel Make Project


## 1. Python 가상환경 세팅

```sh
cd <프로젝트 디렉터리>
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

deactivate
```


## 2. Neo4j 데이터 넣기

neo4j의 `import` 폴더에 현재 프로젝트의 data를 복사해서 넣습니다.
그 후 아래 사이퍼 쿼리를 실행합니다.


```javascript

// city node 생성
LOAD CSV WITH HEADERS FROM "file:///citycode.csv" AS row
CREATE (c:city {city_nm: row.city_name, 
                city_id : row.city_id,
                location : point({latitude:toFloat(row.y), longitude:toFloat(row.x)}),
                latitude:toFloat(row.y), 
                longitude:toFloat(row.x)
                })
;



//LOAD TRANSPORTATION (as relationships)
LOAD CSV with headers from "file:///transportations.csv" as row
MATCH (c1:city),(c2:city)
WHERE c1.city_id = row.depart_id AND c2.city_id = row.dest_id
MERGE (c1)-[r:goes {tid: row.transportation_id, 
                    depart_time:time(row.depart_time), 
                    destination_time: coalesce(row.destination_time,"0"),
                    grade:row.grade, 
                    fare:toInteger(coalesce(row.fare,"0")), 
                    duration:row.duration, 
                    trans_cate:row.trans_cate,                   
                    depart_time_str:row.depart_time,
                    destination_time_str: row.destination_time}
            ]->(c2)
;


//거리넣기
match (a:city)-[r:goes]->(b:city)
set r.dist = (point.distance(a.location, b.location))/1000
;

//토탈거리로 제한걸기 
 MATCH p=(c1:city{city_id:"C01"})-[rels:goes*2..3]->(c2:city{city_id:"C10"})
 WHERE rels[0].depart_time < time('10:00') 
   AND reduce(total=0, r in rels | total+r.dist)<400
RETURN nodes(p) as node,relationships(p) as rels
 LIMIT 500
;





//LOAD attractions 
LOAD CSV WITH HEADERS FROM "file:///attractions.csv" AS row
CREATE (a:attraction {attraction_id: row.attraction_id, 
                      attraction_nm: row.attraction_nm, 
                      address: row.address, 
                      theme: row.theme, 
                      city_nm: row.city_nm, 
                      city_id:row.city_id, 
                      rate : toFloat(row.rate), 
                      longitude:toFloat(row.longitude), 
                      latitude:toFloat(row.latitude)})
;

// Make relationships with attraction to city
MATCH(a:attraction), (c:city)
WHERE a.city_id=c.city_id
MERGE (c)-[has:attraction]->(a)
;

//LOAD restaurants 
LOAD CSV WITH HEADERS FROM "file:///restaurants.csv" AS row
CREATE (r:restaurants {rest_id:row.rest_id, 
                       rest_nm: row.rest_nm, 
                       rest_cat:row.rest_cat, 
                       address: row.address, 
                       city: row.city_nm, 
                       city_id:row.city_id, 
                       rate : toFloat(row.rate),
                       longitude:toFloat(row.longitude), 
                       latitude:toFloat(row.latitude)})
;


// Make relationships with restaurants to city
MATCH(r:restaurants), (c:city)
WHERE r.city_id=c.city_id
MERGE (c)-[has:restaurant]->(r)
;


// LOAD accomodation
LOAD CSV WITH HEADERS FROM "file:///accomodation.csv" AS row
CREATE (ac:accomodation{accom_nm:row.accom_nm,
                        accom_id:row.accom_id,
                        city_id: row.city_id, 
                        accom_nm:row.accom_nm, 
                        address:row.address, 
                        rate:toFloat(row.rate)})
;


// Make relationships with accomodation to city
MATCH(ac:accomodation), (c:city)
WHERE ac.city_id=c.city_id
MERGE (ac)-[has:accomodation]->(r)

```


## 3. Neo4j 사이퍼 쿼리 만들기

흥미로운 사이퍼쿼리를 만듭니다.


**(a) 각 도시별 경로를 리턴하는 쿼리입니다.**

```javasript

MATCH p=(:city{city_id:"C01"})-[rels:goes*1..2]->(:city{city_id:"C22"})
where rels[0].depart_time < time('10:35')
with nodes(p) as cities, p
return distinct cities
;

```

**(b) 교통비 총액이 N원 이상/이하인 경로 찾기**

```javasript

//조건에 sum 붙이기 -- reduce 함수 쓰기
MATCH p=(c1:city{city_nm:"서울"})-[rels:goes*1..2]->(c2:city{city_nm:"강릉"})
where rels[0].depart_time < time('10:35') and reduce(total = 0, r IN rels | total + r.fare)>20000
return p
;

```


