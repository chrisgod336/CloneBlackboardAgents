import queue
import random
import requests
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from flask import Flask, jsonify, request
from threading import Thread

app = Flask(__name__)

# Fila para comunicação entre agentes
message_queue = queue.Queue()

# URL do backend do banco de dados
DB_API_URL = 'http://localhost:5001'

# Estado da aula atual
current_lesson = {
    'lesson_id': 0,
    'content_performance': {'video': [], 'text': [], 'image': []},
    'content_preference': 'text'
}

# Configuração do sistema fuzzy
def setup_fuzzy_content_system():
    video_accuracy = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'video_accuracy')
    text_accuracy = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'text_accuracy')
    image_accuracy = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'image_accuracy')
    content_preference = ctrl.Consequent(np.arange(0, 1.01, 0.01), 'content_preference')
    
    video_accuracy['low'] = fuzz.trimf(video_accuracy.universe, [0, 0, 0.4])
    video_accuracy['high'] = fuzz.trimf(video_accuracy.universe, [0.6, 1, 1])
    text_accuracy['low'] = fuzz.trimf(text_accuracy.universe, [0, 0, 0.4])
    text_accuracy['high'] = fuzz.trimf(text_accuracy.universe, [0.6, 1, 1])
    image_accuracy['low'] = fuzz.trimf(image_accuracy.universe, [0, 0, 0.4])
    image_accuracy['high'] = fuzz.trimf(image_accuracy.universe, [0.6, 1, 1])
    
    content_preference['video'] = fuzz.trimf(content_preference.universe, [0, 0, 0.33])
    content_preference['text'] = fuzz.trimf(content_preference.universe, [0.33, 0.66, 0.66])
    content_preference['image'] = fuzz.trimf(content_preference.universe, [0.66, 1, 1])
    
    rule1 = ctrl.Rule(video_accuracy['high'] & text_accuracy['low'] & image_accuracy['low'], content_preference['video'])
    rule2 = ctrl.Rule(text_accuracy['high'] & video_accuracy['low'] & image_accuracy['low'], content_preference['text'])
    rule3 = ctrl.Rule(image_accuracy['high'] & video_accuracy['low'] & text_accuracy['low'], content_preference['image'])
    rule4 = ctrl.Rule(video_accuracy['low'] & text_accuracy['low'] & image_accuracy['low'], content_preference['text'])
    rule5 = ctrl.Rule(video_accuracy['high'] & text_accuracy['high'] & image_accuracy['high'], content_preference['text'])
    
    system = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5])
    return ctrl.ControlSystemSimulation(system)

class TutorAgent:
    def __init__(self):
        self.fuzzy_content_system = setup_fuzzy_content_system()
    
    def run(self):
        while True:
            if not message_queue.empty():
                msg = message_queue.get()
                if msg['to'] == 'Tutor':
                    if msg['type'] == 'evaluation':
                        current_lesson['content_preference'] = msg['data']['content_preference']
                    elif msg['type'] == 'request_exercise':
                        # Obtém histórico do backend do banco de dados
                        try:
                            response = requests.get(f'{DB_API_URL}/lesson_history')
                            history = response.json()
                        except requests.RequestException:
                            history = []
                        
                        # Calcula taxas de acertos globais
                        video_correct = sum(lesson['video']['correct'] for lesson in history)
                        video_total = sum(lesson['video']['total'] for lesson in history)
                        text_correct = sum(lesson['text']['correct'] for lesson in history)
                        text_total = sum(lesson['text']['total'] for lesson in history)
                        image_correct = sum(lesson['image']['correct'] for lesson in history)
                        image_total = sum(lesson['image']['total'] for lesson in history)
                        
                        video_accuracy = video_correct / max(video_total, 1) if video_total else 0
                        text_accuracy = text_correct / max(text_total, 1) if text_total else 0
                        image_accuracy = image_correct / max(image_total, 1) if image_total else 0
                        
                        # Lógica fuzzy
                        self.fuzzy_content_system.input['video_accuracy'] = video_accuracy
                        self.fuzzy_content_system.input['text_accuracy'] = text_accuracy
                        self.fuzzy_content_system.input['image_accuracy'] = image_accuracy
                        self.fuzzy_content_system.compute()
                        content_score = self.fuzzy_content_system.output['content_preference']
                        new_content = 'video' if content_score <= 0.33 else 'text' if content_score <= 0.66 else 'image'
                        current_lesson['content_preference'] = new_content
                        
                        # Obtém exercícios do backend do banco de dados
                        try:
                            response = requests.get(f'{DB_API_URL}/exercises')
                            exercises = response.json()
                            filtered_exercises = [e for e in exercises if e['type'] == new_content]
                            if not filtered_exercises:
                                filtered_exercises = exercises
                            exercise = random.choice(filtered_exercises)
                        except requests.RequestException:
                            exercise = {'id': 0, 'type': 'text', 'question': 'Erro ao carregar exercício', 'answer': 0, 'url': None}
                        
                        message_queue.put({
                            'to': 'Interface',
                            'type': 'new_exercise',
                            'data': exercise
                        })

class EvaluatorAgent:
    def __init__(self):
        self.fuzzy_content_system = setup_fuzzy_content_system()
    
    def run(self):
        while True:
            if not message_queue.empty():
                msg = message_queue.get()
                if msg['to'] == 'Evaluator' and msg['type'] == 'answer':
                    correct = msg['data']['answer'] == msg['data']['correct_answer']
                    content_type = msg['data']['content_type']
                    
                    current_lesson['content_performance'][content_type].append(correct)
                    
                    # Calcula taxas de acertos da aula atual
                    video_correct = sum(1 for c in current_lesson['content_performance']['video'])
                    video_total = len(current_lesson['content_performance']['video'])
                    text_correct = sum(1 for c in current_lesson['content_performance']['text'])
                    text_total = len(current_lesson['content_performance']['text'])
                    image_correct = sum(1 for c in current_lesson['content_performance']['image'])
                    image_total = len(current_lesson['content_performance']['image'])
                    overall_accuracy = (video_correct + text_correct + image_correct) / max(video_total + text_total + image_total, 1)
                    
                    # Lógica fuzzy para próxima aula
                    self.fuzzy_content_system.input['video_accuracy'] = video_correct / max(video_total, 1) if video_total else 0
                    self.fuzzy_content_system.input['text_accuracy'] = text_correct / max(text_total, 1) if text_total else 0
                    self.fuzzy_content_system.input['image_accuracy'] = image_correct / max(image_total, 1) if image_total else 0
                    self.fuzzy_content_system.compute()
                    content_score = self.fuzzy_content_system.output['content_preference']
                    new_content = 'video' if content_score <= 0.33 else 'text' if content_score <= 0.66 else 'image'
                    
                    # Resultados da aula
                    lesson_results = {
                        'lesson_id': current_lesson['lesson_id'],
                        'video': {'correct': video_correct, 'total': video_total},
                        'text': {'correct': text_correct, 'total': text_total},
                        'image': {'correct': image_correct, 'total': image_total},
                        'overall_accuracy': overall_accuracy
                    }
                    
                    message_queue.put({
                        'to': 'Tutor',
                        'type': 'evaluation',
                        'data': {'content_preference': new_content}
                    })
                    message_queue.put({
                        'to': 'Manager',
                        'type': 'update',
                        'data': {
                            'lesson_results': lesson_results,
                            'content_preference': new_content
                        }
                    })
                    message_queue.put({
                        'to': 'Interface',
                        'type': 'lesson_results',
                        'data': lesson_results
                    })

class ManagerAgent:
    def run(self):
        while True:
            if not message_queue.empty():
                msg = message_queue.get()
                if msg['to'] == 'Manager' and msg['type'] == 'update':
                    # Envia resultados ao backend do banco de dados
                    lesson_results = msg['data']['lesson_results']
                    try:
                        requests.post(f'{DB_API_URL}/lesson_history', json=lesson_results)
                    except requests.RequestException:
                        print("Erro ao salvar resultados no banco de dados")
                    
                    if lesson_results['overall_accuracy'] >= 0.8:
                        message_queue.put({
                            'to': 'Interface',
                            'type': 'feedback',
                            'data': {'message': f'Parabéns! Você está indo bem com {msg["data"]["content_preference"]}!'}
                        })

# Endpoints da API
@app.route('/exercise', methods=['GET'])
def get_exercise():
    global current_lesson
    if not current_lesson['content_performance']['video'] and not current_lesson['content_performance']['text'] and not current_lesson['content_performance']['image']:
        current_lesson['lesson_id'] += 1
        current_lesson['content_performance'] = {'video': [], 'text': [], 'image': []}
    
    message_queue.put({
        'to': 'Tutor',
        'type': 'request_exercise',
        'data': {}
    })
    
    exercise = None
    while not message_queue.empty():
        msg = message_queue.get()
        if msg['to'] == 'Interface' and msg['type'] == 'new_exercise':
            exercise = msg['data']
            break
    
    if exercise:
        return jsonify(exercise)
    return jsonify({'error': 'No exercise available'}), 500

@app.route('/answer', methods=['POST'])
def submit_answer():
    data = request.json
    message_queue.put({
        'to': 'Evaluator',
        'type': 'answer',
        'data': {
            'answer': data['answer'],
            'correct_answer': data['correct_answer'],
            'content_type': data['content_type']
        }
    })
    message_queue.put({
        'to': 'Tutor',
        'type': 'request_exercise',
        'data': {}
    })
    return jsonify({'message': 'Resposta enviada!'})

@app.route('/lesson_results', methods=['GET'])
def get_lesson_results():
    lesson_results = None
    while not message_queue.empty():
        msg = message_queue.get()
        if msg['to'] == 'Interface' and msg['type'] == 'lesson_results':
            lesson_results = msg['data']
            break
    
    if lesson_results:
        return jsonify(lesson_results)
    
    video_correct = sum(1 for c in current_lesson['content_performance']['video'])
    video_total = len(current_lesson['content_performance']['video'])
    text_correct = sum(1 for c in current_lesson['content_performance']['text'])
    text_total = len(current_lesson['content_performance']['text'])
    image_correct = sum(1 for c in current_lesson['content_performance']['image'])
    image_total = len(current_lesson['content_performance']['image'])
    overall_accuracy = (video_correct + text_correct + image_correct) / max(video_total + text_total + image_total, 1)
    
    return jsonify({
        'lesson_id': current_lesson['lesson_id'],
        'video': {'correct': video_correct, 'total': video_total},
        'text': {'correct': text_correct, 'total': text_total},
        'image': {'correct': image_correct, 'total': image_total},
        'overall_accuracy': overall_accuracy
    })

if __name__ == '__main__':
    tutor = TutorAgent()
    evaluator = EvaluatorAgent()
    manager = ManagerAgent()
    
    Thread(target=tutor.run, daemon=True).start()
    Thread(target=evaluator.run, daemon=True).start()
    Thread(target=manager.run, daemon=True).start()
    
    app.run(debug=True, port=5000)