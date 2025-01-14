import redis
import json
import subprocess
import sys

def stop_test_stack():
    print("Arrêt de la stack de test...")
    subprocess.run(['docker', 'compose', '-f', 'docker-compose.test.yml', 'down'])
    print("Stack de test arrêtée.")

r = redis.Redis(host='localhost', port=6379, db=0)
test_message = {
    'user_id': 'user123',
    'position': 1,
    'active_slots': 5,
    'total_slots': 10
}
r.publish(f'queue_status:user123', json.dumps(test_message))
print("Message de test envoyé !")

if __name__ == "__main__":
    try:
        # Votre code de test ici
        print("Tests terminés.")
    finally:
        # Demander à l'utilisateur s'il veut arrêter la stack
        reponse = input("Voulez-vous arrêter la stack de test ? (o/n): ")
        if reponse.lower() == 'o':
            stop_test_stack() 