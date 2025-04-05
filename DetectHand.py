import cv2
import mediapipe as mp
import pyautogui
pyautogui.FAILSAFE = False
import tkinter as tk
from PIL import ImageFont, ImageDraw, Image
import numpy as np
import os
import time
import tkinter as tk
from tkinter import messagebox
import threading

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
screen_width, screen_height = pyautogui.size()

gesture_data = {}

available_actions = {
    "volume_up": "เพิ่มเสียง",
    "volume_down": "ลดเสียง",
    "open_youtube": "เปิด YouTube (Chrome)",
    "left_click": "คลิกซ้าย",
    "youtube_back": "ย้อนกลับใน YouTube",
    "scroll_down": "เลื่อนลง",
    "scroll_up": "เลื่อนขึ้น"
}

font_path = r"C:\Windows\Fonts\Tahoma.ttf"
font = ImageFont.truetype(font_path, 28)
saved_gestures = set()  # ✅ เก็บรายการที่บันทึกท่าไว้

def ask_user_choice():
    """ แสดง UI ให้เลือกคำสั่ง และอัปเดตสีหลังบันทึกท่า """
    root = tk.Tk()
    root.title("เลือกคำสั่ง")
    root.geometry("350x350")

    selected_action = tk.StringVar()

    frame = tk.Frame(root)
    frame.pack(pady=10, padx=10, fill='both', expand=True)

    scrollbar = tk.Scrollbar(frame, orient="vertical")
    scrollbar.pack(side="right", fill="y")

    listbox = tk.Listbox(frame, selectmode="single", yscrollcommand=scrollbar.set, font=("Tahoma", 12))

    # ✅ เพิ่มรายการทั้งหมดเข้าไป
    action_keys = list(available_actions.keys())
    for key in action_keys:
        action_text = f"{available_actions[key]} ({key})"
        listbox.insert(tk.END, action_text)

        # ✅ ถ้าท่านี้ถูกบันทึกแล้ว ให้เปลี่ยนสีเป็น "แดง"
        if key in saved_gestures:
            listbox.itemconfig(tk.END, {'fg': 'red'})

    listbox.pack(fill='both', expand=True)
    scrollbar.config(command=listbox.yview)

    def on_confirm():
        selected = listbox.curselection()
        if selected:
            item_text = listbox.get(selected[0])
            action_key = item_text.split('(')[-1].replace(')', '').strip()
            selected_action.set(action_key)

            # ✅ อัปเดตสีของท่าที่ถูกบันทึก
            saved_gestures.add(action_key)
            listbox.itemconfig(selected[0], {'fg': 'green'})

        root.destroy()

    confirm_button = tk.Button(root, text="ตกลง", command=on_confirm)
    confirm_button.pack(pady=5)

    root.mainloop()

    return selected_action.get() if selected_action.get() else None

def calc_distance(lm1, lm2):
    """ คำนวณระยะห่างระหว่างจุดสองจุด """
    return ((lm1.x - lm2.x) ** 2 + (lm1.y - lm2.y) ** 2) ** 0.5

def show_popup(message):
    """ แสดง Popup แจ้งเตือนแบบ Async """
    def popup():
        root = tk.Tk()
        root.withdraw()  # ซ่อนหน้าต่างหลัก
        messagebox.showinfo("บันทึกสำเร็จ", message)
        root.destroy()

    threading.Thread(target=popup).start()  # ✅ เรียกใช้งานใน Thread แยก

def save_gesture(name, landmarks):
    """ บันทึกท่าทางของมือ โดย Normalize ระยะห่างของนิ้วตามขนาดมือ """
    thumb_cmc = landmarks[mp_hands.HandLandmark.THUMB_CMC]
    pinky_mcp = landmarks[mp_hands.HandLandmark.PINKY_MCP]

    thumb_tip = landmarks[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = landmarks[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = landmarks[mp_hands.HandLandmark.PINKY_TIP]

    # ✅ ใช้ขนาดมือ (Hand Span) เป็นตัว normalize
    hand_span = calc_distance(thumb_cmc, pinky_mcp)
    gesture_data[name] = {
        'thumb_index': calc_distance(thumb_tip, index_tip) / hand_span,
        'index_middle': calc_distance(index_tip, middle_tip) / hand_span,
        'middle_ring': calc_distance(middle_tip, ring_tip) / hand_span,
        'ring_pinky': calc_distance(ring_tip, pinky_tip) / hand_span,
        'hand_span': hand_span  # เก็บค่า hand span ไว้ตรวจสอบภายหลัง
    }

    print(f"บันทึกท่าทาง '{available_actions.get(name, name)}' สำเร็จ!")

    # ✅ เรียก `show_popup()` ใน Thread แยก
    show_popup(f"บันทึกท่าทาง '{available_actions.get(name, name)}' สำเร็จ!")

def compare_gesture(landmarks, saved_data, threshold=0.2):
    """ เปรียบเทียบท่าทางโดย Normalize ระยะห่างของนิ้วกับ Hand Span """
    thumb_cmc = landmarks[mp_hands.HandLandmark.THUMB_CMC]
    pinky_mcp = landmarks[mp_hands.HandLandmark.PINKY_MCP]

    thumb_tip = landmarks[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = landmarks[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = landmarks[mp_hands.HandLandmark.PINKY_TIP]

    # ✅ ใช้ Hand Span ปัจจุบันมาคำนวณ
    hand_span_now = calc_distance(thumb_cmc, pinky_mcp)

    distance_thumb_index_now = calc_distance(thumb_tip, index_tip) / hand_span_now
    distance_index_middle_now = calc_distance(index_tip, middle_tip) / hand_span_now
    distance_middle_ring_now = calc_distance(middle_tip, ring_tip) / hand_span_now
    distance_ring_pinky_now = calc_distance(ring_tip, pinky_tip) / hand_span_now

    # คำนวณความแตกต่าง
    diff_thumb_index = abs(distance_thumb_index_now - saved_data['thumb_index'])
    diff_index_middle = abs(distance_index_middle_now - saved_data['index_middle'])
    diff_middle_ring = abs(distance_middle_ring_now - saved_data['middle_ring'])
    diff_ring_pinky = abs(distance_ring_pinky_now - saved_data['ring_pinky'])

    # ✅ ค่าเฉลี่ยความแตกต่าง
    avg_diff = (diff_thumb_index + diff_index_middle + diff_middle_ring + diff_ring_pinky) / 4

    return avg_diff < threshold


def putTextThai(img, text, position, color=(255, 255, 255), bg_color=(0, 0, 0), padding=10):
    img_pil = Image.fromarray(img)
    draw = ImageDraw.Draw(img_pil)
    text_size = font.getbbox(text)
    text_width = text_size[2] - text_size[0]
    text_height = text_size[3] - text_size[1]
    x, y = position
    draw.rectangle([x - padding, y - padding, x + text_width + padding, y + text_height + padding], fill=bg_color)
    draw.text((x, y), text, font=font, fill=color)
    return np.array(img_pil)

youtube_opened = False
last_action_time = 0
action_cooldown = 0

while True:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    detected_action = None

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            screen_x = int(index_tip.x * screen_width)
            screen_y = int(index_tip.y * screen_height)
            pyautogui.moveTo(screen_x, screen_y)

            current_time = time.time()
            if current_time - last_action_time > action_cooldown:
                for action, saved_data in gesture_data.items():
                    if compare_gesture(hand_landmarks.landmark, saved_data):
                        detected_action = action
                        last_action_time = current_time  # อัปเดตเวลาล่าสุด
                        if action == 'volume_up':
                            pyautogui.press('volumeup')
                            time.sleep(0.1)
                        elif action == 'volume_down':
                            pyautogui.press('volumedown')
                            time.sleep(0.1)
                        elif action == 'open_youtube':
                            os.system('start chrome https://www.youtube.com')
                            time.sleep(2.0)
                        elif action == 'left_click':
                            pyautogui.click()
                            time.sleep(0.2)
                        elif action == 'youtube_back':
                            pyautogui.hotkey('alt', 'left')
                            time.sleep(6.0)
                        elif action == 'scroll_down':
                            pyautogui.scroll(-200)
                            time.sleep(0.2)
                        elif action == 'scroll_up':
                            pyautogui.scroll(200)
                            time.sleep(0.2)

    frame = putTextThai(frame, "กด 's' เพื่อเลือกคำสั่งและบันทึกท่าทาง | 'q' เพื่อออก", (10, 30))
    # วาดข้อความในภาพก่อนการแสดงผล
    if detected_action:
        frame = putTextThai(frame, f"ทำ: {available_actions.get(detected_action, detected_action)}", (10, 80), (0, 255, 0))

    # แสดงภาพที่มีข้อความ
    cv2.imshow("Finger Distance Gesture Control", frame)


    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        selected_action = ask_user_choice()
        if selected_action in available_actions:
            if results.multi_hand_landmarks:
                save_gesture(selected_action, results.multi_hand_landmarks[0].landmark)

cap.release()
cv2.destroyAllWindows()
