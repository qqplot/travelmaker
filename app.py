from crypt import methods
from flask import Flask, render_template, url_for, request
from driver import Neo4jConnection as nc

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
    print(paths[0])

    return render_template('result.html', result= result, all_paths={'paths' : paths})

if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug = True)    
    