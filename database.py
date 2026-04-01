import mysql.connector 
import os
from dotenv import load_dotenv

load_dotenv()


def get_env_data_from_db(querry="SELECT `key`,`value` FROM `user` WHERE `type` = 2"):
    
    try:

        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),        # Your MySQL server address
            user=os.getenv('DB_USER'),    # Your MySQL username
            password=os.getenv('DB_PASS'),# Your MySQL password
            database=os.getenv('DB_NAME'), # Database name
            port=os.getenv('DB_PORT')
        )

        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(querry)
            record = cursor.fetchall()
            return {'success':True,'data':dict(record)}
        
    except Exception as e:
        return {'success':False,'error':str(e)}
        
    finally:
        if 'connection' in globals() and connection.is_connected():
            cursor.close()
            connection.close()


def db_cud(querry=None):
    
    try:

        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),        # Your MySQL server address
            user=os.getenv('DB_USER'),    # Your MySQL username
            password=os.getenv('DB_PASS'),# Your MySQL password
            database=os.getenv('DB_NAME'), # Database name
            port=os.getenv('DB_PORT')
        )

        if connection.is_connected() and querry is not None:
            cursor = connection.cursor()
            cursor.execute(querry)
            connection.commit()
            return {'success':True}
        
    except Exception as e:
        connection.rollback()
        return {'success':False,'error':str(e)}
        
    finally:
        if 'connection' in globals() and connection.is_connected():
            cursor.close()
            connection.close()

