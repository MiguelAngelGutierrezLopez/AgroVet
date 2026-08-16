from flask import Blueprint, request, jsonify

login_bp = Blueprint('login', __name__)

@login_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    # Credenciales hardcodeadas
    if username == 'admin' and password == 'Paola_Milton_Agro26':
        return jsonify({
            'success': True,
            'rol': 'admin',
            'redirect': '/inicio'
        })
    elif username == 'auxiliar' and password == 'AgroVet_Auxiliar':
        return jsonify({
            'success': True,
            'rol': 'auxiliar',
            'redirect': '/prueba'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Usuario o contraseña incorrectos'
        }), 401