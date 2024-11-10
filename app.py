from flask import Flask, render_template, request, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
import datetime
import base64
from io import BytesIO
from PIL import Image
import threading
import openai

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234@localhost/sticker_db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 권장 설정: 추적 수정 경고 끄기
db = SQLAlchemy(app)

# OpenAI API 키 설정
openai.api_key = "sk-" 

# 데이터베이스 모델
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    gender = db.Column(db.String(50))
    age = db.Column(db.String(50))
    department = db.Column(db.String(100))
    photo_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class DiagnosisResult(db.Model):
    __tablename__ = 'diagnosis_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    personal_color = db.Column(db.String(50))
    result_path = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# 데이터베이스 초기화 코드 추가
with app.app_context():
    db.create_all()

# 라우트 정의
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture', methods=['POST'])
def capture():
    # 사용자 정보 저장
    gender = request.form['gender']
    age = request.form['age']
    department = request.form['department']
    user = User(gender=gender, age=age, department=department)
    db.session.add(user)
    db.session.commit()

    # 사진 저장
    photo_data = request.form['photo']
    photo_data = photo_data.replace('data:image/png;base64,', '')
    photo_bytes = base64.b64decode(photo_data)
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{timestamp}.png"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # 이미지 저장
    with open(file_path, 'wb') as f:
        f.write(photo_bytes)

    # 사용자 사진 경로 업데이트
    user.photo_path = file_path
    db.session.commit()

    # 비동기적으로 분석 수행
    threading.Thread(target=analyze_color, args=(user.id, file_path)).start()

    return redirect(url_for('result', user_id=user.id))

def encode_image(image_path):
  print(image_path)
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_color(user_id, file_path):
    tone_result = "봄 웜톤"
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {   
                            "type": "text", 
                            "text": """다음 사용자의 사진에서 옷, 머리색, 피부를 분석해 주세요. 분석기준과 답변은 아래에 있습니다. 해당 조건이 많이 충족된 쪽으로 선택하면 됩니다.

                            - 1: 옷의 채도가 낮고 밝음, 금발이나 밝은 머리색, 피부는 어둡고 노란빛.
                            - 2: 옷의 채도가 낮고 밝음, 어두운 머리색, 피부는 밝고 하얀 빛.
                            - 3: 옷의 채도가 높고 어두움, 갈색빛 머리색, 피부는 어둡고 노란 빛.
                            - 4: 옷의 채도가 높고 어두움, 어두운 머리색, 피부는 밝고 하얀 빛.

                            분석 결과는 다음 네 가지 중 하나로만 답변해 주세요:
                            - 1
                            - 2
                            - 3
                            - 4
                            
                            다른 설명이나 예외 사항 없이, 반드시 위의 네 가지 중 하나로만 답변해 주세요.
                            """ 
                        },
                        {
                            "type": "image_url", 
                            "image_url": {
                                "url": f"data:image/png;base64,{encode_image(file_path)}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=10,
            temperature=0.1,
        )
        tone_result = response.choices[0].message.content

        # 진단 결과 저장
        with app.app_context():
            diagnosis_result = DiagnosisResult(user_id=user_id, personal_color=tone_result)
            db.session.add(diagnosis_result)
            db.session.commit()
    except Exception as e:
        print(f"Error during analyze: {e}")
        return None

@app.route('/result/<int:user_id>')
def result(user_id):
    user = User.query.get(user_id)
    diagnosis_result = DiagnosisResult.query.filter_by(user_id=user_id).first()

    # 결과가 아직 없는 경우 로딩 페이지로 이동
    if not diagnosis_result:
        return render_template('loading.html', user=user)

    return render_template('result.html', user=user, result=diagnosis_result)


@app.route('/four_cut_capture/<int:user_id>', methods=['GET', 'POST'])
def four_cut_capture(user_id):
    user = User.query.get(user_id)
    diagnosis_result = DiagnosisResult.query.filter_by(user_id=user_id).first()
    
    if request.method == 'POST':
        # 네컷 촬영 및 저장 로직
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        frame_color = diagnosis_result.personal_color  # 사용자 퍼스널 컬러에 맞는 프레임 선택
        frame_directory = os.path.join(app.config['UPLOAD_FOLDER'], 'frames')

        # 가정: 프레임 이미지가 `frames` 디렉터리에 저장되어 있음
        frame_paths = {
            '1': os.path.join(frame_directory, 'spring_frame.png'),
            '2': os.path.join(frame_directory, 'summer_frame.png'),
            '3': os.path.join(frame_directory, 'fall_frame.png'),
            '4': os.path.join(frame_directory, 'winter_frame.png')
        }
        frame_path = frame_paths.get(frame_color, frame_paths['1'])  # 디폴트는 봄웜톤 프레임

        # 네컷 사진 합성 로직
        photos = []
        for i in range(4):
            photo_data = request.form.get(f'photo{i+1}')
            if photo_data:
                photo_data = photo_data.replace('data:image/png;base64,', '')
                photo_bytes = base64.b64decode(photo_data)
                photos.append(Image.open(BytesIO(photo_bytes)))

        if photos:
            # 사진과 프레임 합성 후 저장
            frame_image = Image.open(frame_path)
            width, height = frame_image.size
            final_image = Image.new('RGBA', (width, height * 4))
            
            for i, photo in enumerate(photos):
                resized_photo = photo.resize((width, height))
                final_image.paste(resized_photo, (0, height * i))

            final_filename = f'four_cut_{timestamp}.png'
            final_path = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)
            final_image.save(final_path)

            # 결과 저장
            diagnosis_result.result_path = final_path
            db.session.commit()

            return redirect(url_for('result', user_id=user.id))

    return render_template('four_cut.html', user=user, result=diagnosis_result)

@app.route('/save_combined_image/<int:user_id>', methods=['POST'])
def save_combined_image(user_id):
    # 캡처된 프레임 이미지를 받습니다.
    captured_image_data = request.form['captured_image']
    captured_image_data = captured_image_data.replace('data:image/png;base64,', '')
    captured_image_bytes = base64.b64decode(captured_image_data)

    # 이미지를 파일로 저장합니다.
    captured_image = Image.open(io.BytesIO(captured_image_bytes))
    filename = f"combined_{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    captured_image.save(save_path)

    # 결과 경로를 데이터베이스에 저장합니다.
    user_result = DiagnosisResult.query.filter_by(user_id=user_id).first()
    if user_result:
        user_result.result_path = save_path
        db.session.commit()

    return redirect(url_for('result', user_id=user_id))

if __name__ == '__main__':
    app.run(debug=True)
