"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, People, Planets, Vehicles, FavoritePeople, FavoritePlanet, FavoriteVehicle, TokenBlockedList
#from models import Person

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity, get_jwt
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

from datetime import date, time, datetime, timezone, timedelta

from flask_bcrypt import Bcrypt #librería para encriptaciones

app = Flask(__name__)
app.url_map.strict_slashes = False

#inicio de instancia de JWT
app.config["JWT_SECRET_KEY"] = os.getenv("FLASK_APP_KEY")  # Change this!
jwt = JWTManager(app)

bcrypt = Bcrypt(app) #inicio mi instancia de Bcrypt

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)


def verificacionToken(jti):
    jti#Identificador del JWT (es más corto)
    print("jit", jti)
    token = TokenBlockedList.query.filter_by(token=jti).first()

    if token is None:
        return False
    
    return True

@app.route('/user', methods=['GET'])
def handle_hello():
    users = User.query.all()  #<User Antonio>
    users = list(map(lambda item: item.serialize(), users)) #{name:Antonio, password:123, ....} {name:Usuario2, password:123.... }
    print(users)
  
    response_body = {
        "msg": "ok",
        "users": users
    }

    return jsonify(users), 200

@app.route('/register', methods=['POST'])
def register_user():
    body = request.get_json() 

    email = body["email"]
    name = body["name"]
    password = body["password"]
    is_active = body["is_active"]

 
    if body is None:
        raise APIException("You need to specify the request body as json object", status_code=400)
    if "email" not in body:
        raise APIException("You need to specify the email", status_code=400)
    if "name" not in body:
        raise APIException("You need to specify the name", status_code=400)
    if "password" not in body:
        raise APIException("You need to specify the password", status_code=400)
    if "is_active" not in body:
        raise APIException("You need to specify the is_active", status_code=400)

    user = User.query.filter_by(email=email).first()
    if user is not None:
        raise APIException("Email is already registered", status_code=409)

    password_encrypted = bcrypt.generate_password_hash(password,10).decode("utf-8")

   
    new_user = User(email=email, name=name, password=password_encrypted, is_active=is_active)

    #comitear la sesión
    db.session.add(new_user) 
    db.session.commit() 

    return jsonify({"mensaje":"User created successfully"}), 201 

@app.route('/login', methods=['POST'])
def login():
    body = request.get_json()
    email=body["email"]
    password = body["password"]

    user = User.query.filter_by(email=email).first()

    if user is None:
        return jsonify({"message":"Login failed"}), 401


    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message":"Login failed"}), 401
    
    access_token = create_access_token(identity=user.id)
    return jsonify({"token":access_token}), 200

@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"] 
    now = datetime.now(timezone.utc)

   
    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    tokenBlocked = TokenBlockedList(token=jti , created_at=now, email=user.email)
    db.session.add(tokenBlocked)
    db.session.commit()

    return jsonify({"message":"Logout successfully"})

@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():

    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    token = verificacionToken(get_jwt()["jti"]) 
    if token:
       raise APIException('Token is blacklisted', status_code=404)

    print("The user is: ", user.name)
    return jsonify({"message":"You are on a protected route"}), 200

@app.route('/user/<int:id>', methods=['GET'])
def get_specific_user(id):
    user = User.query.get(id)    
  
    return jsonify(user.serialize()), 200

@app.route('/user-with-post', methods=['POST'])
def get_specific_user_with_post():
    body = request.get_json()   
    id = body["id"]

    user = User.query.get(id)   
  
    return jsonify(user.serialize()), 200

@app.route('/user', methods=['DELETE'])
def delete_specific_user():
    body = request.get_json()   
    id = body["id"]

    user = User.query.get(id) 

    db.session.delete(user)
    db.session.commit()  
  
    return jsonify("User deleted"), 200

@app.route('/user', methods=['PUT'])
def edit_user():
    body = request.get_json()   
    id = body["id"]
    name = body["name"]

    if "name" not in body:
        raise APIException("You need to specify the name", status_code=400)
    if "id" not in body:
        raise APIException("You need to specify the id", status_code=400)

    user = User.query.get(id)   
    user.name = name 

    db.session.commit()
  
    return jsonify(user.serialize()), 200


@app.route('/people', methods=['GET'])
def get_all_people():
    people = People.query.all()
    people = list(map(lambda item: item.serialize(), people))


    response_body = {
        "msg": "ok",
        "people": people
    }

    return jsonify(response_body), 200

@app.route('/people', methods=['POST'])
def add_people():
    body = request.get_json()
    name = body["name"]
    birthdate = body["birthdate"]
    gender = body["gender"]
    eyes = body["eyes"]
    skin = body["skin"]
    height = body["height"]

    if body is None:
        raise APIException("You need to specify the request body as json object", status_code=400)
    if "name" not in body:
        raise APIException("You need to specify the name", status_code=400)
    if "birthdate" not in body:
        raise APIException("You need to specify the birthdate", status_code=400)
    if "gender" not in body:
        raise APIException("You need to specify the gender", status_code=400)
    if "eyes" not in body:
        raise APIException("You need to specify the eyes", status_code=400)
    if "skin" not in body:
        raise APIException("You need to specify the skin", status_code=400)
    if "height" not in body:
        raise APIException("You need to specify the height", status_code=400)
    
    new_people = People(name=name, birthdate=birthdate, gender=gender, eyes=eyes, skin=skin, height=height)

    db.session.add(new_people)
    db.session.commit()

    return jsonify({"mensaje":"Character created"}), 201

@app.route('/people/<int:id>', methods=['GET'])
def get_specific_people(id):
    people = People.query.get(id)    
  
    return jsonify(people.serialize()), 200

@app.route('/people-with-post', methods=['POST'])
def get_specific_people_with_post():
    body = request.get_json()   
    id = body["id"]

    people = People.query.get(id)   
  
    return jsonify(people.serialize()), 200

@app.route('/people', methods=['DELETE'])
def delete_specific_people():
    body = request.get_json()   
    id = body["id"]

    people = People.query.get(id)

    db.session.delete(people)
    db.session.commit()  
  
    return jsonify("Deleted character"), 200

@app.route('/people', methods=['PUT'])
def edit_people():
    body = request.get_json()
    name = body["name"]
    birthdate = body["birthdate"]
    gender = body["gender"]
    eyes = body["eyes"]
    skin = body["skin"]
    height = body["height"]

    if body is None:
        raise APIException("You need to specify the request body as json object", status_code=400)
    if "name" not in body:
        raise APIException("You need to specify the name", status_code=400)
    if "birthdate" not in body:
        raise APIException("You need to specify the birthdate", status_code=400)
    if "gender" not in body:
        raise APIException("You need to specify the gender", status_code=400)
    if "eyes" not in body:
        raise APIException("You need to specify the eyes", status_code=400)
    if "skin" not in body:
        raise APIException("You need to specify the skin", status_code=400)
    if "height" not in body:
        raise APIException("You need to specify the height", status_code=400)

    people = People.query.get(id)   
    people.name = name 
    people.birthdate = birthdate
    people.gender = gender
    people.eyes = eyes
    people.skin = skin
    people.height = height

    db.session.commit()
  
    return jsonify(people.serialize()), 200


@app.route('/planets', methods=['GET'])
def get_all_planets():
    planets = Planets.query.all()
    planets = list(map(lambda item: item.serialize(), planets))


    response_body = {
        "msg": "ok",
        "planets": planets
    }

    return jsonify(response_body), 200

@app.route('/planets', methods=['POST'])
def add_planet():
    body = request.get_json()
    name = body["name"]
    gravity = body["gravity"]
    terrain = body["terrain"]
    climate = body["climate"]
    orbital_period = body["orbital period"]
    population = body["population"]
    diameter = body["diameter"]

    if body is None:
        raise APIException("You need to specify the request body as json object", status_code=400)
    if "name" not in body:
        raise APIException("You need to specify the name", status_code=400)
    if "gravity" not in body:
        raise APIException("You need to specify the gravity", status_code=400)
    if "terrain" not in body:
        raise APIException("You need to specify the terrain", status_code=400)
    if "climate" not in body:
        raise APIException("You need to specify the climate", status_code=400)
    if "orbital_period" not in body:
        raise APIException("You need to specify the orbital_period", status_code=400)
    if "population" not in body:
        raise APIException("You need to specify the population", status_code=400)
    if "diameter" not in body:
        raise APIException("You need to specify the diameter", status_code=400)
    
    new_planet = Planets(name=name, gravity=gravity, terrain=terrain, climate=climate, orbital_period=orbital_period, population=population, diameter=diameter)

    db.session.add(new_planet)
    db.session.commit()

    return jsonify({"mensaje":"Planet created successfully"}), 201

@app.route('/planets/<int:id>', methods=['GET'])
def get_specific_planet(id):
    planet = Planets.query.get(id)    
  
    return jsonify(planet.serialize()), 200

@app.route('/planet-with-post', methods=['POST'])
def get_specific_planet_with_post():
    body = request.get_json()   
    id = body["id"]

    planet = Planets.query.get(id)   
  
    return jsonify(planet.serialize()), 200

@app.route('/planets', methods=['DELETE'])
def delete_specific_planet():
    body = request.get_json()   
    id = body["id"]

    planet = Planets.query.get(id) 

    db.session.delete(planet)
    db.session.commit()  
  
    return jsonify("Planet deleted"), 200

@app.route('/planets', methods=['PUT'])
def edit_planet():
    body = request.get_json()
    name = body["name"]
    gravity = body["gravity"]
    terrain = body["terrain"]
    climate = body["climate"]
    orbital_period = body["orbital_period"]
    population = body["population"]
    diameter = body["diameter"]

    if body is None:
        raise APIException("You need to specify the request body as json object", status_code=400)
    if "name" not in body:
        raise APIException("You need to specify the name", status_code=400)
    if "gravity" not in body:
        raise APIException("You need to specify the gravity", status_code=400)
    if "terrain" not in body:
        raise APIException("You need to specify the terrain", status_code=400)
    if "climate" not in body:
        raise APIException("You need to specify the climate", status_code=400)
    if "orbital_period" not in body:
        raise APIException("You need to specify the orbital_period", status_code=400)
    if "population" not in body:
        raise APIException("You need to specify the population", status_code=400)
    if "diameter" not in body:
        raise APIException("You need to specify the diameter", status_code=400)

    planet = Planets.query.get(id)   
    planet.name = name 
    palnet.gravity = gravity
    planet.terrain = terrain
    planet.climate = climate
    planet.orbital_period = orbital_period
    planet.population = population
    planet.diameter = diameter

    db.session.commit()
  
    return jsonify(planet.serialize()), 200



@app.route('/vehicles', methods=['GET'])
def get_all_vehicles():
    vehicles = Vehicles.query.all()
    vehicles = list(map(lambda item: item.serialize(), vehicles))


    response_body = {
        "msg": "ok",
        "vehicles": vehicles
    }

    return jsonify(response_body), 200

@app.route('/vehicles', methods=['POST'])
def add_vehicle():
    body = request.get_json()
    name = body["name"]
    model = body["model"]
    length = body["length"]
    max_speed = body["max_speed"]
    cargo_capacity = body["cargo_capacity"]
    manufacturer = body["manufacturer"]

    if body is None:
        raise APIException("You need to specify the request body as json object", status_code=400)
    if "name" not in body:
        raise APIException("You need to specify the name", status_code=400)
    if "model" not in body:
        raise APIException("You need to specify the model", status_code=400)
    if "length" not in body:
        raise APIException("You need to specify the length", status_code=400)
    if "max_speed" not in body:
        raise APIException("You need to specify the max_speed", status_code=400)
    if "cargo_capacity" not in body:
        raise APIException("You need to specify the cargo_capacity", status_code=400)
    if "manufacturer" not in body:
        raise APIException("You need to specify the manufacturer", status_code=400)
    
    new_vehicle = Vehicles(name=name, model=model, length=length, max_speed=max_speed,cargo_capacity=cargo_capacity, manufacturer=manufacturer)

    db.session.add(new_vehicle)
    db.session.commit()

    return jsonify({"mensaje":"Vehicle created successfully"}), 201

@app.route('/vehicles/<int:id>', methods=['GET'])
def get_specific_vehicle(id):
    vehicle = Vehicles.query.get(id)    
  
    return jsonify(vehicle.serialize()), 200

@app.route('/vehicles-with-post', methods=['POST'])
def get_specific_vehicle_with_post():
    body = request.get_json()   
    id = body["id"]

    vehicle = Vehicles.query.get(id)   
  
    return jsonify(vehicle.serialize()), 200

@app.route('/vehicles', methods=['DELETE'])
def delete_specific_vehicle():
    body = request.get_json()   
    id = body["id"]

    vehicle = Vehicles.query.get(id) 

    db.session.delete(vehicle)
    db.session.commit()  
  
    return jsonify("Vehicle deleted"), 200

@app.route('/vehicles', methods=['PUT'])
def edit_vehicle():
    body = request.get_json()
    name = body["name"]
    model = body["model"]
    length = body["length"]
    max_speed = body["max_speed"]
    cargo_capacity = body["cargo_capacity"]
    manufacturer = body["manufacturer"]

    if body is None:
        raise APIException("You need to specify the request body as json object", status_code=400)
    if "name" not in body:
        raise APIException("You need to specify the name", status_code=400)
    if "model" not in body:
        raise APIException("You need to specify the model", status_code=400)
    if "length" not in body:
        raise APIException("You need to specify the length", status_code=400)
    if "max_speed" not in body:
        raise APIException("You need to specify the max_speed", status_code=400)
    if "cargo_capacity" not in body:
        raise APIException("You need to specify the cargo_capacity", status_code=400)
    if "manufacturer" not in body:
        raise APIException("You need to specify the manufacturer", status_code=400)

    vehicle = Vehicles.query.get(id)   
    vehicle.name = name 
    vehicle.model = model
    vehicle.length = length
    vehicle.max_speed = max_speed
    vehicle.cargo_capacity = cargo_capacity
    manufacturer = manufacturer

    db.session.commit()
  
    return jsonify(vehicle.serialize()), 200


@app.route('/favorite/people', methods=['POST'])
def add_favorite_people():
    body = request.get_json()
    user_id = body["user_id"]
    people_id = body["people_id"]

    character = People.query.get(people_id)
    if not character:
        raise APIException('Character not found', status_code=404)
    
    user = User.query.get(user_id)
    if not user:
        raise APIException('User not found', status_code=404)

    fav_exist = FavoritePeople.query.filter_by(user_id = user.id, people_id = character.id).first() is not None
    
    if fav_exist:
        raise APIException('The user has already added it to favorites', status_code=400)

    favorite_people = FavoritePeople(user_id=user.id, people_id=character.id)
    db.session.add(favorite_people)
    db.session.commit()

    return jsonify({
        "people_name":favorite_people.serialize()["people_name"],
        "user": favorite_people.serialize()["user_name"]
    }), 201

@app.route('/favorite/people', methods=['DELETE'])
def remove_favorite_people():
    body = request.get_json()
    user_id = body["user_id"]
    people_id = body["people_id"]

    favorite_people = FavoritePeople.query.filter_by(user_id=user_id, people_id=people_id).first()

    if not favorite_people:
        raise APIException('Favorite people not found', status_code=404)

    db.session.delete(favorite_people)
    db.session.commit()

    return jsonify({"msg":"Favorite people removed successfully"}), 200

@app.route('/favorite/planet', methods=['POST'])
def add_favorite_planet():
    body = request.get_json()
    user_id = body["user_id"]
    planet_id = body["planet_id"]

    planet = Planets.query.get(planet_id)
    if not planet:
        raise APIException('Planet not found', status_code=404)
    
    user = User.query.get(user_id)
    if not user:
        raise APIException('User not found', status_code=404)

    fav_exist = FavoritePlanet.query.filter_by(user_id = user.id, planet_id = planet.id).first() is not None
    
    if fav_exist:
        raise APIException('The user has already added it to favorites', status_code=400)

    favorite_planet = FavoritePlanet(user_id=user.id, planet_id=planet.id)
    db.session.add(favorite_planet)
    db.session.commit()

    return jsonify({
        "planet_name":favorite_planet.serialize()["planet_name"],
        "user": favorite_planet.serialize()["user_name"]
    }), 201

@app.route('/favorite/planet', methods=['DELETE'])
def remove_favorite_planet():
    body = request.get_json()
    user_id = body["user_id"]
    planet_id = body["planet_id"]

    favorite_planet = FavoritePlanet.query.filter_by(user_id=user_id, planet_id=planet_id).first()

    if not favorite_planet:
        raise APIException('Favorite planet not found', status_code=404)

    db.session.delete(favorite_planet)
    db.session.commit()

    return jsonify({"msg":"Favorite planet removed successfully"}), 200

@app.route('/favorite/vehicle', methods=['POST'])
def add_favorite_vehicle():
    body = request.get_json()
    user_id = body["user_id"]
    vehicle_id = body["vehicle_id"]

    vehicle = Vehicles.query.get(vehicle_id)
    if not vehicle:
        raise APIException('Vehicle not found', status_code=404)

    user = User.query.get(user_id)
    if not user:
        raise APIException('User not found', status_code=404)

    fav_exist = FavoriteVehicle.query.filter_by(user_id=user.id, vehicle_id=vehicle.id).first() is not None

    if fav_exist:
        raise APIException('The user has already added it to favorites', status_code=400)

    favorite_vehicle = FavoriteVehicle(user_id=user.id, vehicle_id=vehicle.id)
    db.session.add(favorite_vehicle)
    db.session.commit()

    return jsonify({
        "vehicle_name": favorite_vehicle.serialize()["vehicle_name"],
        "user": favorite_vehicle.serialize()["user_name"]
    }), 201


@app.route('/favorite/vehicle', methods=['DELETE'])
def remove_favorite_vehicle():
    body = request.get_json()
    user_id = body["user_id"]
    vehicle_id = body["vehicle_id"]

    favorite_vehicle = FavoriteVehicle.query.filter_by(user_id=user_id, vehicle_id=vehicle_id).first()

    if not favorite_vehicle:
        raise APIException('Favorite vehicle not found', status_code=404)

    db.session.delete(favorite_vehicle)
    db.session.commit()

    return jsonify({"msg": "Favorite vehicle removed successfully"}), 200

@app.route('/favorites', methods=['POST'])
def get_favorites_with_post():
    body = request.get_json()
    user_id = body["user_id"]

    if user_id is None:
        raise APIException("You need to specify the user_id as a query parameter", status_code=400)

    user = User.query.get(user_id)
    if not user:
        raise APIException('User not found', status_code=404)

    favorite_people = list(map(lambda item: {"name": item.serialize()["people_name"], "id": item.serialize()["people_id"], "url": "/people"}, FavoritePeople.query.filter_by(user_id=user.id)))
    favorite_planet = list(map(lambda item: {"name": item.serialize()["planet_name"], "id": item.serialize()["planet_id"], "url": "/planets"}, FavoritePlanet.query.filter_by(user_id=user.id)))
    favorite_vehicle = list(map(lambda item: {"name": item.serialize()["vehicle_name"], "id": item.serialize()["vehicle_id"], "url": "/vehicles"}, FavoriteVehicle.query.filter_by(user_id=user.id)))

    return jsonify({
        "msg":"ok",
        "all_favorites": favorite_people + favorite_planet + favorite_vehicle,
    }), 200

@app.route('/favorites/<int:user_id>', methods=['GET'])
@jwt_required()
def get_favorites(user_id):
    current_user = get_jwt_identity()
    if user_id != current_user:
        raise APIException('Unauthorized', status_code=401)
    
    user = User.query.get(user_id)
    if not user:
        raise APIException('User not found', status_code=404)

    token = verificacionToken(get_jwt()["jti"])
    if token:
       raise APIException('Token está en lista negra', status_code=404)

    favorite_people = list(map(lambda item: {"name": item.serialize()["people_name"], "id": item.serialize()["people_id"], "url": "/people"}, FavoritePeople.query.filter_by(user_id=current_user)))
    favorite_planet = list(map(lambda item: {"name": item.serialize()["planet_name"], "id": item.serialize()["planet_id"], "url": "/planets"}, FavoritePlanet.query.filter_by(user_id=current_user)))
    favorite_vehicle = list(map(lambda item: {"name": item.serialize()["vehicle_name"], "id": item.serialize()["vehicle_id"], "url": "/vehicles"}, FavoriteVehicle.query.filter_by(user_id=current_user)))

    return jsonify({
        "msg":"ok",
        "all_favorites": favorite_people + favorite_planet + favorite_vehicle,
    }), 200



# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
