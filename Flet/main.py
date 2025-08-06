import flet as ft
import time
import s2t.s2t as s2t
import threading
import asyncio
from src.OllamaBackend import CanaryTopicModel,base_model
from src.question_generator import QuestionGenerator
from ollama import chat
from pydantic import BaseModel
import sys
import os

# Suppress pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
sys.path.append(os.path.join(os.path.dirname(__file__), 't2s'))
import t2s as t2s
import pygame

from storage.data.DB.DB_API import TopicsDB
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from simple_spider_graph import get_radar_chart_path

# -- Theme & Constants -- #
BG_COLOR = "#4a4a4a"
CONTAINER_BG = "#bcb8b1"
TEXT_FIELD_BG = "#e0e0e0"
TEXT_COLOR = "#f5f5f5"
BLACK_TEXT = "#2e2e2e"
FONT_FAMILY = "Cairo"
TOPIC_NAME = "Baye's theorem"

# Global state
tts_playing = False
tts_thread = None
topics_db = TopicsDB()

# -- Pydantic Models -- #
class Question(BaseModel):
    question: str
    options: list[str]
    correct_answer: str
    explanation: str

class Flashcard(BaseModel):
    question: str
    answer: str

class FlashcardDeck(BaseModel):
    topic: str
    cards: list[Flashcard]

# -- Reusable Components -- #
def AppLogo(size=80):
    return ft.Container(
        content=ft.Image(
            src=r"storage\data\img\BigLogo.png",
            width=size,
            height=size,
            fit=ft.ImageFit.CONTAIN,
        ),
        tooltip="Teaching shows true understanding."
    )

def SmallLogo(size=32):
    return ft.Image(
        src=r"storage\data\img\SmallLogo.png",
        width=size,
        height=size,
        fit=ft.ImageFit.CONTAIN,
    )

def IconButton(icon_path, size=50, on_click=None, tooltip="", bg_color=TEXT_FIELD_BG, loading=False):
    return ft.IconButton(
        content=ft.Stack([
            ft.Image(src=icon_path, width=size, height=size),
            ft.ProgressRing(width=size, height=size, visible=loading, stroke_width=3, color=BLACK_TEXT)
        ]) if loading else ft.Image(src=icon_path, width=size, height=size),
        icon_size=size,
        icon_color=BLACK_TEXT,
        tooltip=tooltip,
        bgcolor=bg_color,
        style=ft.ButtonStyle(shape=ft.CircleBorder(), padding=20),
        on_click=on_click,
        disabled=loading
    )

def main(page: ft.Page):
    # Page setup
    page.window.width = 800
    page.window.height = 1200
    page.window.resizable = False 
    page.title = "Canary Offline"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG_COLOR
    page.fonts = {
        "Cairo": "storage/data/fonts/Cairo.ttf",
        "Courgette-Regular": "storage/data/fonts/Courgette-Regular.ttf"
    }
    page.theme = ft.Theme(font_family=FONT_FAMILY)

    # State variables
    recording_state = {"is_recording": False}
    progress_ring = ft.Ref[ft.ProgressRing]()
    progress_bar_timer = {"thread": None, "stop": False}
    canary_model = CanaryTopicModel(base_model=base_model, topic=TOPIC_NAME)
    question_generator = QuestionGenerator()
    last_canary_response = ""
    tts_playing = False
    current_topic_id = None
    current_topic_name = TOPIC_NAME
    notes_field = ft.Ref[ft.TextField]()
    last_notes = ""
    
    # Response field
    canary_response = ft.TextField(
        multiline=True,
        min_lines=8,
        bgcolor=TEXT_FIELD_BG,
        border_radius=8,
        border_width=0,
        height=160,
        read_only=True,
        value=""
    )
    canary_loading = ft.ProgressRing(visible=False, width=20, height=20)

    # -- Core Functions -- #
    def update_canary_topic(new_topic):
        nonlocal current_topic_name
        current_topic_name = new_topic
        canary_model.set_topic(new_topic)

    def create_new_topic_from_input(topic_name: str):
        if not topic_name.strip():
            page.snack_bar = ft.SnackBar(content=ft.Text("Please enter a topic name", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
            page.snack_bar.open = True
            page.update()
            return
        
        try:
            new_topic = topics_db.create_topic(topic_name.strip())
            nonlocal current_topic_id, current_topic_name
            current_topic_id = int(new_topic['id'])
            current_topic_name = new_topic['topic_name']
            update_canary_topic(current_topic_name)
            page.go("/main")
            page.snack_bar = ft.SnackBar(content=ft.Text(f"Topic '{current_topic_name}' created!", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            print(f"[Database] Error: {e}")
            page.snack_bar = ft.SnackBar(content=ft.Text("Error creating topic", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
            page.snack_bar.open = True
            page.update()

    def select_topic_and_go_main(topic_id: int):
        try:
            topic = topics_db.get_topic_by_id(topic_id)
            if topic:
                nonlocal current_topic_id, current_topic_name
                current_topic_id = topic_id
                current_topic_name = topic['topic_name']
                update_canary_topic(current_topic_name)
                # Store notes to be loaded when main view is created
                nonlocal last_notes
                last_notes = topic.get('notes', '')
                page.go("/main")
        except Exception as e:
            print(f"[Database] Error: {e}")
            page.snack_bar = ft.SnackBar(content=ft.Text("Error selecting topic", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
            page.snack_bar.open = True
            page.update()

    def save_progress():
        if current_topic_id is None:
            page.snack_bar = ft.SnackBar(content=ft.Text("No topic selected", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
            page.snack_bar.open = True
            page.update()
            return
        try:
            # Safely get notes text from the field
            notes_text = ""
            if notes_field.current:
                try:
                    notes_text = notes_field.current.value or ""
                except Exception:
                    notes_text = ""
            topics_db.update_topic(current_topic_id, notes=notes_text)
            page.snack_bar = ft.SnackBar(content=ft.Text("Progress saved!", color=TEXT_COLOR), bgcolor=CONTAINER_BG, duration=2000)
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            print(f"[Database] Error: {e}")
            page.snack_bar = ft.SnackBar(content=ft.Text("Error saving", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
            page.snack_bar.open = True
            page.update()

    def get_statistics():
        try:
            return topics_db.get_statistics()
        except Exception as e:
            print(f"[Database] Error: {e}")
            return {'total_topics': 0, 'topics_today': 0, 'total_study_time': 0, 'average_study_time': 0, 'study_streak': 0, 'most_studied_topic': None, 'recent_topics': []}

    def generate_spider_graph():
        try:
            graph_path = get_radar_chart_path()
            return graph_path if graph_path and os.path.exists(graph_path) else None
        except Exception as e:
            print(f"[Spider Graph] Error: {e}")
            return None

    # -- TTS Functions -- #
    def speak_text(text):
        nonlocal tts_playing
        if tts_playing:
            stop_speech()
        try:
            tts_playing = True
            tts_thread = threading.Thread(target=run_tts, args=(text,), daemon=True)
            tts_thread.start()
        except Exception as e:
            print(f"[TTS] Error: {e}")
            tts_playing = False
    
    def run_tts(text):
        try:
            asyncio.run(t2s.t2s(text))
        except Exception as e:
            print(f"[TTS] Error: {e}")
        finally:
            nonlocal tts_playing
            tts_playing = False
    
    def stop_speech():
        nonlocal tts_playing
        if tts_playing:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                tts_playing = False
            except Exception as e:
                print(f"[TTS] Error: {e}")

    # -- Recording Functions -- #
    def update_progress_ring():
        while recording_state["is_recording"] and not progress_bar_timer["stop"]:
            elapsed = s2t.get_recording_progress()
            value = min(elapsed / s2t.RECORD_TIME, 1.0)
            if progress_ring.current:
                progress_ring.current.value = value
                progress_ring.current.visible = True
                progress_ring.current.update()
            time.sleep(0.1)
        if progress_ring.current:
            progress_ring.current.visible = False
            progress_ring.current.value = 0
            progress_ring.current.update()

    def on_transcription(result):
        canary_response.value = result
        canary_response.update()
        canary_loading.visible = True
        canary_loading.update()
        
        try:
            canary_learning_response = canary_model.generate_response(result)
            canary_response.value = canary_learning_response
            canary_response.update()
            nonlocal last_canary_response
            last_canary_response = canary_learning_response
            speak_text(canary_learning_response)
        except Exception as e:
            print(f"[Canary] Error: {e}")
            try:
                fallback_response = canary_model.stream_response(result)
                canary_response.value = fallback_response
                canary_response.update()
                speak_text(fallback_response)
            except Exception as fallback_error:
                print(f"[Fallback] Error: {fallback_error}")
        finally:
            canary_loading.visible = False
            canary_loading.update()
    
    s2t.set_on_transcription_callback(on_transcription)

    def toggle_recording(e=None):
        if recording_state["is_recording"]:
            result = s2t.stop_recording_and_transcribe()
            recording_state["is_recording"] = False
            progress_bar_timer["stop"] = True
            canary_loading.visible = True
            canary_loading.update()
            
            try:
                canary_learning_response = canary_model.generate_response(result)
                canary_response.value = canary_learning_response
                canary_response.update()
                nonlocal last_canary_response
                last_canary_response = canary_learning_response
                speak_text(canary_learning_response)
            except Exception as e:
                print(f"[Canary] Error: {e}")
                try:
                    fallback_response = canary_model.stream_response(result)
                    canary_response.value = fallback_response
                    canary_response.update()
                    speak_text(fallback_response)
                except Exception as fallback_error:
                    print(f"[Fallback] Error: {fallback_error}")
            finally:
                canary_loading.visible = False
                canary_loading.update()
        else:
            started = s2t.start_recording()
            if not started:
                return
            recording_state["is_recording"] = True
            progress_bar_timer["stop"] = False
            t = threading.Thread(target=update_progress_ring, daemon=True)
            progress_bar_timer["thread"] = t
            t.start()

    def generate_question(e):
        try:
            canary_loading.visible = True
            canary_loading.update()
            
            response = chat(
                model='gemma3n:e2b-it-q4_K_M',
                messages=[{
                    'role': 'user', 
                    'content': f'Generate a single multiple choice question about {current_topic_name} with 4 options (A, B, C, D) and explanation.'
                }],
                stream=False,
                format=Question.model_json_schema(),
            )
            
            question = Question.model_validate_json(response['message']['content'])
            question_text = f"Question: {question.question}\n\nOptions:\n"
            for i, option in enumerate(['A', 'B', 'C', 'D']):
                question_text += f"{option}. {question.options[i]}\n"
            question_text += f"\nCorrect Answer: {question.correct_answer}\nExplanation: {question.explanation}"
            
            canary_response.value = question_text
            canary_response.update()
            
            # Only speak if TTS is not stopped
            if not tts_playing:
                speak_text(question_text)
            
        except Exception as e:
            print(f"[Question Generator] Error: {e}")
            canary_response.value = "Error generating question. Please try again."
            canary_response.update()
        finally:
            canary_loading.visible = False
            canary_loading.update()

    # -- Views -- #
    def create_topics_view():
        stats = get_statistics()
        recent_topics = topics_db.get_recent_topics(5)
        
        topic_name_input = ft.TextField(
            label="Name of topic to study",
            text_style=ft.TextStyle(color=BLACK_TEXT),
            width=300,
            bgcolor=TEXT_FIELD_BG,
            border_radius=8,
            focused_border_color="#0d0d0d",
        )
        
        def handle_create_topic(e):
            topic_name = topic_name_input.value
            if topic_name:
                create_new_topic_from_input(topic_name)
                topic_name_input.value = ""
                topic_name_input.update()
        
        recent_topics_list = []
        if recent_topics:
            for topic in recent_topics:
                topic_container = ft.Container(
                    ft.Row([
                        ft.Column([
                            ft.Text(f"{topic['topic_name']}", weight=ft.FontWeight.BOLD, color=BLACK_TEXT),
                            ft.Text(f"Created: {topic['date']}", color=BLACK_TEXT, size=12)
                        ]),
                        ft.ElevatedButton(
                            "Select", 
                            bgcolor=TEXT_FIELD_BG, 
                            color=BLACK_TEXT, 
                            on_click=lambda e, t=topic: select_topic_and_go_main(int(t['id']))
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10,
                    bgcolor=TEXT_FIELD_BG,
                    border_radius=8,
                    width=300,
                    margin=ft.margin.only(bottom=10)
                )
                recent_topics_list.append(topic_container)
        else:
            recent_topics_list.append(
                ft.Container(
                    ft.Text("No topics created yet", color=BLACK_TEXT, size=16),
                    padding=10,
                    bgcolor=TEXT_FIELD_BG,
                    border_radius=8,
                    width=300
                )
            )
        
        return ft.View(
            "/",
            bgcolor=BG_COLOR,
            appbar=ft.AppBar(
                leading=AppLogo(60),
                leading_width=200,
                title=ft.Text("Topics", size=48, font_family="Courgette-Regular", color=TEXT_COLOR),
                center_title=True,
                bgcolor=CONTAINER_BG,
            ),
            controls=[
                ft.Container(
                    content=ft.Column([
                        # Top Row: Create & Select Topics
                        ft.Row([
                            # Create Topic
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Create topic", size=36, color=TEXT_COLOR, font_family="Courgette-Regular"),
                                    topic_name_input,
                                    ft.ElevatedButton("Create", bgcolor=CONTAINER_BG, color=BLACK_TEXT, on_click=handle_create_topic),
                                    ft.Container(height=40),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                                padding=20,
                                bgcolor=CONTAINER_BG,
                                border_radius=12,
                                expand=True,
                            ),
                            
                            # Select Topic
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Recent topics", size=36, color=TEXT_COLOR, font_family="Courgette-Regular"),
                                    ft.Container(
                                        content=ft.Column(recent_topics_list, spacing=5, scroll=ft.ScrollMode.AUTO, height=200),
                                        padding=10,
                                        bgcolor=CONTAINER_BG,
                                        border_radius=8,
                                        width=320
                                    )
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                                padding=20,
                                bgcolor=CONTAINER_BG,
                                border_radius=12,
                                expand=True,
                            ),
                        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                        
                        # Study Time Distribution Graph (moved under Recent Topics)
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Study Time Distribution (Last 7 Days)", size=20, color=TEXT_COLOR, font_family="Courgette-Regular", weight=ft.FontWeight.BOLD),
                                ft.Container(
                                    content=ft.Image(
                                        src=generate_spider_graph() or r"storage\data\img\BigLogo.png",
                                        width=400,
                                        height=300,
                                        fit=ft.ImageFit.CONTAIN,
                                    ),
                                    padding=10,
                                    bgcolor=TEXT_FIELD_BG,
                                    border_radius=8,
                                    alignment=ft.alignment.center,
                                ),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                            padding=15,
                            bgcolor=CONTAINER_BG,
                            border_radius=12,
                            margin=ft.margin.only(top=15),
                        ),
                        
                        # Statistics Section (Chess Board Style)
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Study Statistics", size=30, color=TEXT_COLOR, font_family="Courgette-Regular", weight=ft.FontWeight.BOLD),
                                # Chess board pattern with alternating colors
                                ft.Column([
                                    ft.Row([
                                        ft.Container(
                                            content=ft.Column([
                                                ft.Text(f"Topics created today: {stats['topics_today']}", color=BLACK_TEXT, size=24),
                                                ft.Text(f"Total topics: {stats['total_topics']}", color=BLACK_TEXT, size=24),
                                            ], spacing=8),
                                            padding=15,
                                            bgcolor="#e8e8e8",  # Light square
                                            border_radius=8,
                                            expand=True,
                                        ),
                                        ft.Container(
                                            content=ft.Column([
                                                ft.Text(f"Study streak: {stats['study_streak']} days", color=BLACK_TEXT, size=24),
                                                ft.Text(f"Average study time: {stats['average_study_time']} min", color=BLACK_TEXT, size=24),
                                            ], spacing=8),
                                            padding=15,
                                            bgcolor="#d0d0d0",  # Dark square
                                            border_radius=8,
                                            expand=True,
                                        ),
                                    ], spacing=20),
                                    ft.Row([
                                        ft.Container(
                                            content=ft.Column([
                                                ft.Text(f"Most studied topic: {stats['most_studied_topic'] or 'None'}", color=BLACK_TEXT, size=24),
                                                ft.Text(f"Total study time: {stats['total_study_time']} min", color=BLACK_TEXT, size=24),
                                            ], spacing=8),
                                            padding=15,
                                            bgcolor="#d0d0d0",  # Dark square
                                            border_radius=8,
                                            expand=True,
                                        ),
                                        ft.Container(
                                            content=ft.Column([
                                                ft.Text("Study Progress", color=BLACK_TEXT, size=24, weight=ft.FontWeight.BOLD),
                                                ft.Text("Keep up the great work!", color=BLACK_TEXT, size=20),
                                            ], spacing=8),
                                            padding=15,
                                            bgcolor="#e8e8e8",  # Light square
                                            border_radius=8,
                                            expand=True,
                                        ),
                                    ], spacing=20),
                                ], spacing=10),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            padding=20,
                            bgcolor=CONTAINER_BG,
                            border_radius=12,
                            margin=ft.margin.only(top=20),
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, scroll=ft.ScrollMode.AUTO),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def create_main_view():
        # Create button refs for loading states
        question_button_ref = ft.Ref[ft.IconButton]()
        quiz_button_ref = ft.Ref[ft.IconButton]()
        flashcards_button_ref = ft.Ref[ft.IconButton]()
        mic_button_ref = ft.Ref[ft.IconButton]()
        
        # Loading states
        question_loading = {"is_loading": False}
        quiz_loading = {"is_loading": False}
        flashcards_loading = {"is_loading": False}
        
        def update_question_button_loading(loading: bool):
            question_loading["is_loading"] = loading
            if question_button_ref.current:
                question_button_ref.current.disabled = loading
                question_button_ref.current.content = ft.Stack([
                    ft.Image(src=r"storage\data\img\ques.png", width=50, height=50),
                    ft.ProgressRing(width=50, height=50, visible=loading, stroke_width=3, color=BLACK_TEXT)
                ]) if loading else ft.Image(src=r"storage\data\img\ques.png", width=50, height=50)
                question_button_ref.current.update()
        
        def update_quiz_button_loading(loading: bool):
            quiz_loading["is_loading"] = loading
            if quiz_button_ref.current:
                quiz_button_ref.current.disabled = loading
                quiz_button_ref.current.content = ft.Stack([
                    ft.Image(src=r"storage\data\img\mcq.png", width=50, height=50),
                    ft.ProgressRing(width=50, height=50, visible=loading, stroke_width=3, color=BLACK_TEXT)
                ]) if loading else ft.Image(src=r"storage\data\img\mcq.png", width=50, height=50)
                quiz_button_ref.current.update()
        
        def update_flashcards_button_loading(loading: bool):
            flashcards_loading["is_loading"] = loading
            if flashcards_button_ref.current:
                flashcards_button_ref.current.disabled = loading
                flashcards_button_ref.current.content = ft.Stack([
                    ft.Image(src=r"storage\data\img\cards.png", width=50, height=50),
                    ft.ProgressRing(width=50, height=50, visible=loading, stroke_width=3, color=BLACK_TEXT)
                ]) if loading else ft.Image(src=r"storage\data\img\cards.png", width=50, height=50)
                flashcards_button_ref.current.update()
        
        def update_mic_button_loading(loading: bool):
            if mic_button_ref.current:
                mic_button_ref.current.disabled = loading
                mic_button_ref.current.content = ft.Stack([
                    ft.Image(src=r"storage\data\img\mic.png", width=50, height=50),
                    ft.ProgressRing(width=50, height=50, visible=loading, stroke_width=3, color=BLACK_TEXT)
                ]) if loading else ft.Image(src=r"storage\data\img\mic.png", width=50, height=50)
                mic_button_ref.current.update()
        
        def generate_question_with_loading(e):
            update_question_button_loading(True)
            try:
                generate_question(e)
            finally:
                update_question_button_loading(False)
        
        def go_to_quiz_with_loading(e):
            update_quiz_button_loading(True)
            try:
                page.go("/quiz")
            finally:
                update_quiz_button_loading(False)
        
        def go_to_flashcards_with_loading(e):
            update_flashcards_button_loading(True)
            try:
                page.go("/flashcards")
            finally:
                update_flashcards_button_loading(False)
        
        def toggle_recording_with_loading(e):
            update_mic_button_loading(True)
            try:
                toggle_recording(e)
            finally:
                update_mic_button_loading(False)
        
        return ft.View(
            "/main",
            bgcolor=BG_COLOR,
            appbar=ft.AppBar(
                leading=IconButton(r"storage\data\img\home.png", 32, lambda _: page.go("/"), "Home"),
                title=AppLogo(60),
                center_title=True,
                bgcolor=CONTAINER_BG,
                actions=[
                    ft.Container(
                        content=ft.Row([
                            ft.Image(src=r"storage\data\img\Fire.png", width=32, height=32),
                            ft.Text(f"Streak: {get_statistics()['study_streak']}", weight=ft.FontWeight.BOLD, color=BLACK_TEXT, font_family="Courgette-Regular")
                        ]),
                        padding=ft.padding.symmetric(horizontal=20, vertical=15),
                    )
                ]
            ),
            controls=[
                ft.Row([ft.Text(f"{current_topic_name}", color=TEXT_COLOR, size=45, font_family="Courgette-Regular")], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([
                    # Left: Response and Notes
                    ft.Column([
                        ft.Text("Canary Response:", color=TEXT_COLOR, size=27, font_family=FONT_FAMILY),
                        ft.Column([
                            canary_response,
                            canary_loading
                        ], spacing=10),
                        ft.Text("Notes:", color=TEXT_COLOR, size=27, font_family=FONT_FAMILY),
                        ft.TextField(
                            ref=notes_field,
                            multiline=True,
                            min_lines=8,
                            bgcolor=TEXT_FIELD_BG,
                            border_radius=8,
                            border_width=0,
                            height=160,
                            value=last_notes,
                        ),
                    ], expand=4),
                    
                    # Right: Action Buttons
                    ft.Column([
                        ft.Container(
                            ft.Column([
                                # Mic Button with Progress Ring
                                ft.Stack([
                                    ft.Container(
                                        ft.ProgressRing(ref=progress_ring, value=0, width=80, height=80, visible=False, stroke_width=8, color=BLACK_TEXT),
                                        alignment=ft.alignment.center,
                                        width=80, height=80,
                                    ),
                                    ft.Container(
                                        ft.IconButton(
                                            ref=mic_button_ref,
                                            content=ft.Image(src=r"storage\data\img\mic.png", width=50, height=50),
                                            icon_size=50,
                                            icon_color=BLACK_TEXT if not recording_state["is_recording"] else "#e53935",
                                            tooltip="Start Speaking" if not recording_state["is_recording"] else "Stop Recording",
                                            bgcolor=TEXT_FIELD_BG,
                                            style=ft.ButtonStyle(shape=ft.CircleBorder(), padding=0),
                                            width=80, height=80,
                                            on_click=toggle_recording_with_loading
                                        ),
                                        alignment=ft.alignment.center,
                                        width=80, height=80,
                                    ),
                                ]),
                                
                                # Action Buttons
                                ft.IconButton(
                                    ref=question_button_ref,
                                    content=ft.Image(src=r"storage\data\img\ques.png", width=50, height=50),
                                    icon_size=50,
                                    icon_color=BLACK_TEXT,
                                    tooltip="Generate Question",
                                    bgcolor=TEXT_FIELD_BG,
                                    style=ft.ButtonStyle(shape=ft.CircleBorder(), padding=20),
                                    on_click=generate_question_with_loading
                                ),
                                ft.IconButton(
                                    ref=quiz_button_ref,
                                    content=ft.Image(src=r"storage\data\img\mcq.png", width=50, height=50),
                                    icon_size=50,
                                    icon_color=BLACK_TEXT,
                                    tooltip="Test Me",
                                    bgcolor=TEXT_FIELD_BG,
                                    style=ft.ButtonStyle(shape=ft.CircleBorder(), padding=20),
                                    on_click=go_to_quiz_with_loading
                                ),
                                ft.IconButton(
                                    ref=flashcards_button_ref,
                                    content=ft.Image(src=r"storage\data\img\cards.png", width=50, height=50),
                                    icon_size=50,
                                    icon_color=BLACK_TEXT,
                                    tooltip="Flashcards",
                                    bgcolor=TEXT_FIELD_BG,
                                    style=ft.ButtonStyle(shape=ft.CircleBorder(), padding=20),
                                    on_click=go_to_flashcards_with_loading
                                ),
                                
                                # Stop TTS Button (using mute icon instead of text)
                                ft.IconButton(
                                    content=ft.Image(src=r"storage\data\img\mute.png", width=50, height=50),
                                    icon_size=50,
                                    icon_color="#e53935" if tts_playing else BLACK_TEXT,
                                    tooltip="Stop Talking",
                                    bgcolor="#e53935" if tts_playing else TEXT_FIELD_BG,
                                    style=ft.ButtonStyle(shape=ft.CircleBorder(), padding=20),
                                    on_click=lambda _: stop_speech()
                                ),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                            padding=20,
                            border_radius=8,
                            bgcolor=CONTAINER_BG
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                ], spacing=20, vertical_alignment=ft.CrossAxisAlignment.START),
                
                # Save Button
                ft.Column([
                    ft.ElevatedButton("Save Progress", bgcolor=CONTAINER_BG, color=BLACK_TEXT, on_click=lambda _: save_progress()),
                    ft.Text("CANARY CAN MAKE MISTAKE.", color=TEXT_COLOR, size=15)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5, width=page.width),
            ],
            padding=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def create_quiz_view():
        # Quiz loading state
        quiz_loading = ft.ProgressRing(visible=True, width=30, height=30)
        quiz_content = ft.Ref[ft.Container]()
        
        def load_quiz():
            try:
                # Generate a single question like the generate_question function
                response = chat(
                    model='gemma3n:e2b-it-q4_K_M',
                    messages=[{
                        'role': 'user', 
                        'content': f'Generate a single multiple choice question about {current_topic_name} with 4 options (A, B, C, D) and explanation.'
                    }],
                    stream=False,
                    format=Question.model_json_schema(),
                )
                
                question = Question.model_validate_json(response['message']['content'])
                selected_answer = ft.Ref[ft.RadioGroup]()
                score_display = ft.Ref[ft.Text]()

                def build_question_row(question: Question):
                    return ft.Container(
                        content=ft.Column([
                            ft.Text(f"Test Question: {question.question}", size=20, color=BLACK_TEXT, font_family=FONT_FAMILY, weight=ft.FontWeight.BOLD),
                            ft.RadioGroup(
                                ref=selected_answer,
                                content=ft.Column([
                                    ft.Radio(value="a", label=question.options[0], label_position=ft.LabelPosition.RIGHT),
                                    ft.Radio(value="b", label=question.options[1], label_position=ft.LabelPosition.RIGHT),
                                    ft.Radio(value="c", label=question.options[2], label_position=ft.LabelPosition.RIGHT),
                                    ft.Radio(value="d", label=question.options[3], label_position=ft.LabelPosition.RIGHT),
                                ], spacing=8),
                            ),
                        ], spacing=10),
                        padding=15,
                        bgcolor=TEXT_FIELD_BG,
                        border_radius=8,
                        margin=ft.margin.only(bottom=15)
                    )

                def submit_quiz(e):
                    selected = selected_answer.current.value if selected_answer.current else None
                    is_correct = selected and selected.lower() == question.correct_answer.lower()
                    
                    score_text = f"Score: {'1/1 (100%)' if is_correct else '0/1 (0%)'}"
                    score_display.current.value = score_text
                    score_display.current.update()
                    
                    # Show explanation
                    explanation_text = f"{score_text}\n\nExplanation: {question.explanation}"
                    page.snack_bar = ft.SnackBar(content=ft.Text(explanation_text, color=TEXT_COLOR), bgcolor=CONTAINER_BG, duration=5000)
                    page.snack_bar.open = True
                    page.update()
                
                # Create quiz content
                quiz_container = ft.Container(
                    content=ft.Column([
                        ft.Text(f"Test: {current_topic_name}", size=36, weight=ft.FontWeight.BOLD, color=BLACK_TEXT, font_family="Courgette-Regular"),
                        ft.Text(ref=score_display, size=24, color=BLACK_TEXT, font_family=FONT_FAMILY, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=build_question_row(question),
                            bgcolor=CONTAINER_BG,
                            border_radius=8,
                            padding=15,
                        ),
                        ft.Row([ft.ElevatedButton("SUBMIT", bgcolor=CONTAINER_BG, color=BLACK_TEXT, on_click=submit_quiz)], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                        ft.Text("CANARY CAN MAKE MISTAKE.", color=BLACK_TEXT, size=15)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                    padding=20,
                    bgcolor=BG_COLOR,
                    border_radius=12,
                )
                
                # Update the view
                if quiz_content.current:
                    quiz_content.current.content = quiz_container.content
                    quiz_content.current.update()
                quiz_loading.visible = False
                quiz_loading.update()
                
            except Exception as e:
                print(f"[Quiz Loading] Error: {e}")
                quiz_loading.visible = False
                quiz_loading.update()
                if quiz_content.current:
                    quiz_content.current.content = ft.Text("Error loading quiz. Please try again.", color=TEXT_COLOR, size=20)
                    quiz_content.current.update()
        
        # Start loading quiz in background
        threading.Thread(target=load_quiz, daemon=True).start()
        
        return ft.View(
            "/quiz",
            bgcolor=BG_COLOR,
            appbar=ft.AppBar(
                leading=IconButton(r"storage\data\img\back.png", 24, lambda _: page.go("/main"), "Back"),
                title=AppLogo(60),
                center_title=True,
                bgcolor=CONTAINER_BG,
            ),
            controls=[
                ft.Container(
                    content=ft.Column([
                        quiz_loading,
                        ft.Container(ref=quiz_content, content=ft.Text("Generating test question...", color=TEXT_COLOR, size=16)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            ],
            padding=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

    def create_flashcards_view():
        # Flashcards loading state
        flashcards_loading = ft.ProgressRing(visible=True, width=30, height=30)
        flashcards_content = ft.Ref[ft.Container]()
        
        def load_flashcards():
            try:
                # Get existing flashcards for the current topic
                existing_flashcards = []
                try:
                    existing_flashcards = topics_db.get_flashcards_by_topic(current_topic_id) if current_topic_id else []
                except:
                    existing_flashcards = []
                
                # Create input fields for new flashcard
                question_input = ft.TextField(
                    label="Question", 
                    width=300, 
                    bgcolor=TEXT_FIELD_BG, 
                    border_radius=8, 
                    focused_border_color="#0d0d0d",
                    text_style=ft.TextStyle(color=BLACK_TEXT)
                )
                answer_input = ft.TextField(
                    label="Answer", 
                    width=300, 
                    bgcolor=TEXT_FIELD_BG, 
                    border_radius=8, 
                    focused_border_color="#0d0d0d",
                    text_style=ft.TextStyle(color=BLACK_TEXT)
                )
                
                # Create a list view for existing flashcards
                flashcards_list = ft.ListView(
                    spacing=10,
                    auto_scroll=False,
                    height=400,
                )
                
                def add_flashcard(e):
                    question_text = question_input.value
                    answer_text = answer_input.value
                    if question_text.strip() and answer_text.strip():
                        try:
                            topics_db.add_flashcard(current_topic_id, question_text.strip(), answer_text.strip())
                            # Add new flashcard to the list
                            new_card = ft.Container(
                                content=ft.Column([
                                    ft.Text(f"Q: {question_text.strip()}", size=20, color=BLACK_TEXT, font_family=FONT_FAMILY, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"A: {answer_text.strip()}", size=20, color=BLACK_TEXT, font_family=FONT_FAMILY),
                                ], spacing=5),
                                padding=15,
                                bgcolor=TEXT_FIELD_BG,
                                border_radius=8,
                                margin=ft.margin.only(bottom=10)
                            )
                            flashcards_list.controls.append(new_card)
                            flashcards_list.update()
                            
                            # Clear inputs
                            question_input.value = ""
                            answer_input.value = ""
                            question_input.update()
                            answer_input.update()
                            
                            page.snack_bar = ft.SnackBar(content=ft.Text("Flashcard added!", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
                            page.snack_bar.open = True
                            page.update()
                        except Exception as e:
                            print(f"[Flashcard] Error: {e}")
                            page.snack_bar = ft.SnackBar(content=ft.Text("Error adding flashcard", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
                            page.snack_bar.open = True
                            page.update()
                    else:
                        page.snack_bar = ft.SnackBar(content=ft.Text("Question and Answer cannot be empty", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
                        page.snack_bar.open = True
                        page.update()
                
                # Add existing flashcards to the list
                for card in existing_flashcards:
                    card_container = ft.Container(
                        content=ft.Column([
                            ft.Text(f"Q: {card['question']}", size=20, color=BLACK_TEXT, font_family=FONT_FAMILY, weight=ft.FontWeight.BOLD),
                            ft.Text(f"A: {card['answer']}", size=20, color=BLACK_TEXT, font_family=FONT_FAMILY),
                        ], spacing=5),
                        padding=15,
                        bgcolor=TEXT_FIELD_BG,
                        border_radius=8,
                        margin=ft.margin.only(bottom=10)
                    )
                    flashcards_list.controls.append(card_container)
                
                # Study mode functionality
                def start_study_mode(e):
                    if not existing_flashcards:
                        page.snack_bar = ft.SnackBar(content=ft.Text("No flashcards to study!", color=TEXT_COLOR), bgcolor=CONTAINER_BG)
                        page.snack_bar.open = True
                        page.update()
                        return
                    page.go("/study-flashcards")
                
                # Create flashcards content
                flashcards_container = ft.Container(
                    content=ft.Column([
                        ft.Text(f"Flashcards for: {current_topic_name}", size=36, weight=ft.FontWeight.BOLD, color=TEXT_COLOR, font_family="Courgette-Regular"),
                        
                        # Study Mode Button
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Study Mode", size=24, color=TEXT_COLOR, font_family="Courgette-Regular"),
                                ft.ElevatedButton("Start Studying", bgcolor=CONTAINER_BG, color=BLACK_TEXT, on_click=start_study_mode),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            padding=20,
                            bgcolor=CONTAINER_BG,
                            border_radius=12,
                        ),
                        
                        # Add New Flashcard Section
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Add New Flashcard", size=24, color=TEXT_COLOR, font_family="Courgette-Regular"),
                                question_input,
                                answer_input,
                                ft.ElevatedButton("Add Flashcard", bgcolor=CONTAINER_BG, color=BLACK_TEXT, on_click=add_flashcard),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            padding=20,
                            bgcolor=CONTAINER_BG,
                            border_radius=12,
                        ),
                        
                        # Existing Flashcards Section
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Your Flashcards", size=24, color=TEXT_COLOR, font_family="Courgette-Regular"),
                                ft.Container(
                                    content=flashcards_list,
                                    padding=15,
                                    bgcolor=CONTAINER_BG,
                                    border_radius=8,
                                ),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            padding=20,
                            bgcolor=CONTAINER_BG,
                            border_radius=12,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                    alignment=ft.alignment.center,
                    expand=True,
                )
                
                # Update the view
                if flashcards_content.current:
                    flashcards_content.current.content = flashcards_container.content
                    flashcards_content.current.update()
                flashcards_loading.visible = False
                flashcards_loading.update()
                
            except Exception as e:
                print(f"[Flashcards Loading] Error: {e}")
                flashcards_loading.visible = False
                flashcards_loading.update()
                if flashcards_content.current:
                    flashcards_content.current.content = ft.Text("Error loading flashcards. Please try again.", color=TEXT_COLOR, size=20)
                    flashcards_content.current.update()
        
        # Start loading flashcards in background
        threading.Thread(target=load_flashcards, daemon=True).start()
        
        return ft.View(
            "/flashcards",
            bgcolor=BG_COLOR,
            appbar=ft.AppBar(
                leading=IconButton(r"storage\data\img\back.png", 24, lambda _: page.go("/main"), "Back"),
                title=AppLogo(60),
                center_title=True,
                bgcolor=CONTAINER_BG,
            ),
            controls=[
                ft.Container(
                    content=ft.Column([
                        flashcards_loading,
                        ft.Container(ref=flashcards_content, content=ft.Text("Loading your flashcards...", color=TEXT_COLOR, size=16)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            ],
            padding=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def create_study_flashcards_view():
        # Get flashcards for the current topic
        flashcards = []
        try:
            flashcards = topics_db.get_flashcards_by_topic(current_topic_id) if current_topic_id else []
        except:
            flashcards = []
        
        if not flashcards:
            return ft.View(
                "/study-flashcards",
                bgcolor=BG_COLOR,
                appbar=ft.AppBar(
                    leading=IconButton(r"storage\data\img\back.png", 24, lambda _: page.go("/flashcards"), "Back"),
                    title=AppLogo(60),
                    center_title=True,
                    bgcolor=CONTAINER_BG,
                ),
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Text("No Flashcards", size=36, weight=ft.FontWeight.BOLD, color=TEXT_COLOR, font_family="Courgette-Regular"),
                            ft.Text("Create some flashcards first!", size=20, color=TEXT_COLOR, font_family=FONT_FAMILY),
                            ft.ElevatedButton("Go Back", bgcolor=CONTAINER_BG, color=BLACK_TEXT, on_click=lambda _: page.go("/flashcards")),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                        alignment=ft.alignment.center,
                        expand=True,
                    )
                ],
                padding=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        
        # Study mode state
        current_card_index = 0
        showing_answer = False
        
        # Create card display
        card_display = ft.Container(
            content=ft.Column([
                ft.Text("Q:", size=24, color=BLACK_TEXT, font_family=FONT_FAMILY, weight=ft.FontWeight.BOLD),
                ft.Text(flashcards[0]['question'], size=20, color=BLACK_TEXT, font_family=FONT_FAMILY),
                ft.Container(height=20),
                ft.Text("A:", size=24, color=BLACK_TEXT, font_family=FONT_FAMILY, weight=ft.FontWeight.BOLD, visible=False),
                ft.Text(flashcards[0]['answer'], size=20, color=BLACK_TEXT, font_family=FONT_FAMILY, visible=False),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=30,
            bgcolor=TEXT_FIELD_BG,
            border_radius=12,
            width=500,
            height=300,
            alignment=ft.alignment.center,
        )
        
        # Navigation buttons
        prev_button = ft.ElevatedButton("Previous", bgcolor=CONTAINER_BG, color=BLACK_TEXT, disabled=True)
        next_button = ft.ElevatedButton("Next", bgcolor=CONTAINER_BG, color=BLACK_TEXT)
        flip_button = ft.ElevatedButton("Show Answer", bgcolor=CONTAINER_BG, color=BLACK_TEXT)
        
        # Progress indicator
        progress_text = ft.Text(f"Card {current_card_index + 1} of {len(flashcards)}", size=16, color=TEXT_COLOR, font_family=FONT_FAMILY)
        
        def update_card_display():
            if 0 <= current_card_index < len(flashcards):
                card = flashcards[current_card_index]
                card_display.content.controls[1].value = card['question']
                card_display.content.controls[3].visible = showing_answer
                card_display.content.controls[4].value = card['answer']
                card_display.content.controls[4].visible = showing_answer
                card_display.update()
                
                progress_text.value = f"Card {current_card_index + 1} of {len(flashcards)}"
                progress_text.update()
                
                # Update button states
                prev_button.disabled = current_card_index == 0
                next_button.disabled = current_card_index == len(flashcards) - 1
                prev_button.update()
                next_button.update()
        
        def show_previous_card(e):
            nonlocal current_card_index, showing_answer
            if current_card_index > 0:
                current_card_index -= 1
                showing_answer = False
                update_card_display()
                flip_button.text = "Show Answer"
                flip_button.update()
        
        def show_next_card(e):
            nonlocal current_card_index, showing_answer
            if current_card_index < len(flashcards) - 1:
                current_card_index += 1
                showing_answer = False
                update_card_display()
                flip_button.text = "Show Answer"
                flip_button.update()
        
        def flip_card(e):
            nonlocal showing_answer
            showing_answer = not showing_answer
            card_display.content.controls[3].visible = showing_answer
            card_display.content.controls[4].visible = showing_answer
            card_display.update()
            flip_button.text = "Hide Answer" if showing_answer else "Show Answer"
            flip_button.update()
        
        # Set up button callbacks
        prev_button.on_click = show_previous_card
        next_button.on_click = show_next_card
        flip_button.on_click = flip_card
        
        return ft.View(
            "/study-flashcards",
            bgcolor=BG_COLOR,
            appbar=ft.AppBar(
                leading=IconButton(r"storage\data\img\back.png", 24, lambda _: page.go("/flashcards"), "Back"),
                title=AppLogo(60),
                center_title=True,
                bgcolor=CONTAINER_BG,
            ),
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Study Flashcards: {current_topic_name}", size=36, weight=ft.FontWeight.BOLD, color=TEXT_COLOR, font_family="Courgette-Regular"),
                        progress_text,
                        card_display,
                        ft.Row([
                            prev_button,
                            flip_button,
                            next_button,
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                        ft.Text("Click 'Show Answer' to reveal the answer", size=14, color=TEXT_COLOR, font_family=FONT_FAMILY),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            ],
            padding=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # -- Routing -- #
    def route_change(route):
        page.views.clear()
        if page.route == "/main":
            page.views.append(create_main_view())
        elif page.route == "/quiz":
            page.views.append(create_quiz_view())
        elif page.route == "/flashcards":
            page.views.append(create_flashcards_view())
        elif page.route == "/study-flashcards":
            page.views.append(create_study_flashcards_view())
        else:
            page.views.append(create_topics_view())
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)

if __name__ == "__main__":
    ft.app(target=main)
