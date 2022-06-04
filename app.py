from crypt import methods
from flask import Flask, render_template, url_for, request
from driver import Neo4jConnection as nc, GoogleBigQueryConnection as gc
import random

neo4j_uri = "bolt://localhost:7687"
neo4j_user = "neo4j"
neo4j_pwd = "0097"

app = Flask(__name__, static_url_path="/templates/")
# app.config['SERVER_NAME'] = 'flask.dev'

@app.route('/')
def map_func():
	return render_template('index.html')

@app.route('/result', methods=['POST'])
def get_result():
    if request.method == 'POST':
        result = request.form

    if result is None:
        return "404 Error!"
    
    conn = nc(uri=neo4j_uri, user=neo4j_user, pwd=neo4j_pwd)

    theme = result['theme']
    city_id_from = result['from']
    city_id_to = result['to']
    depart_time  = result['depart_time'] 
    days = result['days']

    paths = nc.getPaths(conn, city_id_from, city_id_to, depart_time, days)

    conn.close()
    # Path별 칼라 생성
    pathColorList = []
    for _ in range(len(paths)):
        color = "#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)])
        pathColorList.append(color)

    # Detail 정보를 위한 도시 노드 리턴
    cities = nc.get_unique_city(paths)

    # 구글 빅쿼리에서 Detail 정보를 가져온다.
    conn = gc()
 
    details = {}
    idx = 0
    for city in cities:
        print(city)
        key, value = gc.recommend(conn, city[1], city[0], theme, city[3], city[2])
        details[key] = value
        
    conn.close()

    return render_template('result.html', 
        result=result, 
        all_paths={'paths' : paths}, 
        pathColorList=pathColorList, detailInfo=details)



if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug = True)    
    