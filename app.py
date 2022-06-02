from crypt import methods
from flask import Flask, render_template, url_for, request
app = Flask(__name__, static_url_path="/templates/")
# app.config['SERVER_NAME'] = 'flask.dev'

@app.route('/')
def map_func():
	return render_template('index.html')

@app.route('/result', methods=['POST'])
def get_result():
    if request.method == 'POST':
        result = request.form

    return render_template('result.html', result= result)

if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug = True)    
    