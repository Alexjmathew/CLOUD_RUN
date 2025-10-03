from flask import Flask, render_template, Response
import cv2
import mediapipe as mp
import numpy as np

app = Flask(__name__)

# Initialize MediaPipe Pose solution
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def calculate_angle(a, b, c):
    """
    Calculates the angle formed by three points (a, b, c), where b is the vertex.
    The angle is calculated in degrees.
    """
    a = np.array(a)  # First point (e.g., shoulder)
    b = np.array(b)  # Mid point (e.g., elbow)
    c = np.array(c)  # End point (e.g., wrist)
    
    # Calculate the vectors between the points
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    # Ensure the angle is between 0 and 180
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def generate_frames():
    """Generator function to yield video frames."""
    cap = cv2.VideoCapture(0)
    
    # Bicep curl counter variables
    counter = 0 
    stage = None # Can be 'down' or 'up'

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            
            # Recolor image from BGR to RGB for MediaPipe
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
          
            # Make detection
            results = pose.process(image)
        
            # Recolor back to BGR for rendering
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            # Extract landmarks
            try:
                landmarks = results.pose_landmarks.landmark
                
                # Get coordinates for the left arm.
                # You can change this to RIGHT_SHOULDER, etc. for the right arm.
                shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
                
                # Calculate angle
                angle = calculate_angle(shoulder, elbow, wrist)
                
                # Visualize the angle on the frame
                cv2.putText(image, str(int(angle)), 
                               tuple(np.multiply(elbow, [640, 480]).astype(int)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                
                # --- Curl counter logic ---
                # The arm is considered 'down' when the angle is high (extended).
                if angle > 160:
                    stage = "down"
                # The arm is 'up' (flexed) and a rep is counted when the angle is low
                # and the arm was previously 'down'.
                if angle < 30 and stage == 'down':
                    stage = "up"
                    counter += 1
                    print(f"Rep Count: {counter}")
                           
            except:
                # This block will be executed if landmarks are not detected
                pass
            
            # --- Render curl counter and stage info ---
            # Setup a status box
            cv2.rectangle(image, (0,0), (225,73), (245,117,16), -1)
            
            # Display "REPS" text
            cv2.putText(image, 'REPS', (15,12), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1, cv2.LINE_AA)
            # Display the counter value
            cv2.putText(image, str(counter), 
                        (10,60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2, cv2.LINE_AA)
            
            # Display "STAGE" text
            cv2.putText(image, 'STAGE', (95,12), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1, cv2.LINE_AA)
            # Display the current stage
            cv2.putText(image, stage, 
                        (80,60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2, cv2.LINE_AA)
            
            # Render pose detections on the image
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                    mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2), 
                                    mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2) 
                                     )               
            
            # Encode the frame in JPEG format
            ret, buffer = cv2.imencode('.jpg', image)
            frame_bytes = buffer.tobytes()
            
            # Yield the frame in the correct format for streaming
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    cap.release()

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
