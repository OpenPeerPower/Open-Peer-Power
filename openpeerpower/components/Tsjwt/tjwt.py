from datetime import datetime, timedelta
import jwt

JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 20


def main():
    payload = {
        'user_id': 'paul',
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
    print(jwt_token)

main()
    if secret is None:
        secret = opp.data[DATA_SIGN_SECRET] = generate_secret()

    now = dt_util.utcnow()
    return "{}?{}={}".format(path, SIGN_QUERY_PARAM, jwt.encode({
        'iss': refresh_token_id,
        'path': path,
        'iat': now,
        'exp': now + expiration,
    }, secret, algorithm='HS256').decode())