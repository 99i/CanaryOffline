import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

class TopicsDB:
    def __init__(self, csv_file_path: str = "TopicesDB.csv"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_file_path = os.path.join(current_dir, csv_file_path)
        self.fieldnames = ['id', 'topic_name', 'notes', 'date', 'time_spend']
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writeheader()
    
    def _get_next_id(self) -> int:
        topics = self.get_all_topics()
        if not topics:
            return 1
        # Filter out topics with invalid IDs and handle None/empty values
        valid_ids = []
        for topic in topics:
            try:
                if topic.get('id') and str(topic['id']).strip():
                    valid_ids.append(int(topic['id']))
            except (ValueError, TypeError):
                continue
        return max(valid_ids) + 1 if valid_ids else 1
    
    def create_topic(self, topic_name: str, notes: str = "", time_spend: int = 0) -> Dict:
        topic_id = self._get_next_id()
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        new_topic = {
            'id': str(topic_id),
            'topic_name': topic_name,
            'notes': notes,
            'date': current_date,
            'time_spend': str(time_spend)
        }
        
        with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writerow(new_topic)
        
        return new_topic
    
    def get_all_topics(self) -> List[Dict]:
        topics = []
        try:
            with open(self.csv_file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    topics.append(row)
        except FileNotFoundError:
            pass
        return topics
    
    def get_topic_by_id(self, topic_id: int) -> Optional[Dict]:
        topics = self.get_all_topics()
        for topic in topics:
            try:
                if topic.get('id') and str(topic['id']).strip() and int(topic['id']) == topic_id:
                    return topic
            except (ValueError, TypeError):
                continue
        return None
    
    def get_topic_by_name(self, topic_name: str) -> Optional[Dict]:
        topics = self.get_all_topics()
        for topic in topics:
            if topic['topic_name'].lower() == topic_name.lower():
                return topic
        return None
    
    def update_topic(self, topic_id: int, **kwargs) -> Optional[Dict]:
        topics = self.get_all_topics()
        updated_topic = None
        
        for topic in topics:
            try:
                if topic.get('id') and str(topic['id']).strip() and int(topic['id']) == topic_id:
                    for key, value in kwargs.items():
                        if key in self.fieldnames and key != 'id':
                            topic[key] = str(value)
                    updated_topic = topic
                    break
            except (ValueError, TypeError):
                continue
        
        if updated_topic:
            self._write_all_topics(topics)
        
        return updated_topic
    
    def delete_topic(self, topic_id: int) -> bool:
        topics = self.get_all_topics()
        original_count = len(topics)
        filtered_topics = []
        
        for topic in topics:
            try:
                if topic.get('id') and str(topic['id']).strip() and int(topic['id']) != topic_id:
                    filtered_topics.append(topic)
            except (ValueError, TypeError):
                # Keep topics with invalid IDs
                filtered_topics.append(topic)
        
        if len(filtered_topics) < original_count:
            self._write_all_topics(filtered_topics)
            return True
        return False
    
    def _write_all_topics(self, topics: List[Dict]):
        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(topics)
    
    def get_recent_topics(self, limit: int = 5) -> List[Dict]:
        topics = self.get_all_topics()
        # Filter out topics with invalid IDs for sorting
        valid_topics = []
        for topic in topics:
            try:
                if topic.get('id') and str(topic['id']).strip():
                    valid_topics.append(topic)
            except (ValueError, TypeError):
                continue
        
        sorted_topics = sorted(valid_topics, key=lambda x: (x['date'], int(x['id'])), reverse=True)
        return sorted_topics[:limit]
    
    def get_today_topics(self) -> List[Dict]:
        today = datetime.now().strftime('%Y-%m-%d')
        topics = self.get_all_topics()
        return [topic for topic in topics if topic['date'] == today]
    
    def get_statistics(self) -> Dict:
        topics = self.get_all_topics()
        
        if not topics:
            return {
                'total_topics': 0,
                'topics_today': 0,
                'total_study_time': 0,
                'average_study_time': 0,
                'study_streak': 0,
                'most_studied_topic': None,
                'recent_topics': []
            }
        
        total_topics = len(topics)
        topics_today = len(self.get_today_topics())
        total_study_time = 0
        for topic in topics:
            try:
                time_spend = topic.get('time_spend', '0')
                if time_spend and str(time_spend).strip():
                    total_study_time += int(time_spend)
            except (ValueError, TypeError):
                continue
        average_study_time = total_study_time / total_topics if total_topics > 0 else 0
        
        topic_study_time = {}
        for topic in topics:
            try:
                topic_name = topic['topic_name']
                time_spend = topic.get('time_spend', '0')
                if time_spend and str(time_spend).strip():
                    study_time = int(time_spend)
                    topic_study_time[topic_name] = topic_study_time.get(topic_name, 0) + study_time
            except (ValueError, TypeError):
                continue
        
        most_studied_topic = max(topic_study_time.items(), key=lambda x: x[1]) if topic_study_time else None
        study_dates = sorted(list(set(topic['date'] for topic in topics)), reverse=True)
        study_streak = self._calculate_streak(study_dates)
        recent_topics = self.get_recent_topics(5)
        
        return {
            'total_topics': total_topics,
            'topics_today': topics_today,
            'total_study_time': total_study_time,
            'average_study_time': round(average_study_time, 1),
            'study_streak': study_streak,
            'most_studied_topic': most_studied_topic[0] if most_studied_topic else None,
            'recent_topics': recent_topics
        }
    
    def _calculate_streak(self, study_dates: List[str]) -> int:
        if not study_dates:
            return 0
        
        today = datetime.now().date()
        streak = 0
        current_date = today
        
        for study_date in study_dates:
            study_date_obj = datetime.strptime(study_date, '%Y-%m-%d').date()
            
            if study_date_obj == current_date:
                streak += 1
                current_date = current_date - timedelta(days=1)
            elif study_date_obj < current_date:
                break
        
        return streak
    
    def search_topics(self, query: str) -> List[Dict]:
        topics = self.get_all_topics()
        query_lower = query.lower()
        
        matching_topics = []
        for topic in topics:
            if (query_lower in topic['topic_name'].lower() or 
                query_lower in topic['notes'].lower()):
                matching_topics.append(topic)
        
        return matching_topics

    # Flashcard methods
    def _get_flashcards_file_path(self, topic_id: int) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, f"flashcards_{topic_id}.csv")
    
    def _ensure_flashcards_csv_exists(self, topic_id: int):
        file_path = self._get_flashcards_file_path(topic_id)
        if not os.path.exists(file_path):
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['id', 'question', 'answer', 'created_date'])
                writer.writeheader()
    
    def add_flashcard(self, topic_id: int, question: str, answer: str) -> Dict:
        self._ensure_flashcards_csv_exists(topic_id)
        file_path = self._get_flashcards_file_path(topic_id)
        
        # Get existing flashcards to determine next ID
        existing_flashcards = self.get_flashcards_by_topic(topic_id)
        valid_ids = []
        for card in existing_flashcards:
            try:
                if card.get('id') and str(card['id']).strip():
                    valid_ids.append(int(card['id']))
            except (ValueError, TypeError):
                continue
        next_id = max(valid_ids) + 1 if valid_ids else 1
        
        new_flashcard = {
            'id': str(next_id),
            'question': question,
            'answer': answer,
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(file_path, 'a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['id', 'question', 'answer', 'created_date'])
            writer.writerow(new_flashcard)
        
        return new_flashcard
    
    def get_flashcards_by_topic(self, topic_id: int) -> List[Dict]:
        file_path = self._get_flashcards_file_path(topic_id)
        flashcards = []
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        flashcards.append(row)
            except FileNotFoundError:
                pass
        
        return flashcards
    
    def delete_flashcard(self, topic_id: int, flashcard_id: int) -> bool:
        file_path = self._get_flashcards_file_path(topic_id)
        flashcards = self.get_flashcards_by_topic(topic_id)
        original_count = len(flashcards)
        
        filtered_flashcards = []
        for card in flashcards:
            try:
                if card.get('id') and str(card['id']).strip() and int(card['id']) != flashcard_id:
                    filtered_flashcards.append(card)
            except (ValueError, TypeError):
                # Keep cards with invalid IDs
                filtered_flashcards.append(card)
        
        if len(filtered_flashcards) < original_count:
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['id', 'question', 'answer', 'created_date'])
                writer.writeheader()
                writer.writerows(filtered_flashcards)
            return True
        return False

