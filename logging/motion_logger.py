from flask import Flask, Response, request

app = Flask(__name__)

@app.route('/log', methods=['POST'])
def log():
    # retrieve data
    motion_factor = float(request.data)
    
    # scale up smaller values
    motion_factor = motion_factor ** 0.25

    print('motion_factor', motion_factor)
    return Response(status=200)

if __name__ == '__main__':
    app.run(port=3001)
