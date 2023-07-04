from flask import Flask, Response, request

app = Flask(__name__)

@app.route('/log', methods=['POST'])
def log():
    motion_factor = float(request.data)
    print('motion_factor', request.data)
    return Response(status=200)

if __name__ == '__main__':
    app.run(port=3001)
