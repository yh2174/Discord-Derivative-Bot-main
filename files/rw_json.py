import json
import os
from typing import TypedDict, List, Dict, Any, Optional

class roles_json_typehint(TypedDict):
    available_role_ids: List
    transform_table : Dict[str, bool]

class tickets_json_typehint(TypedDict):
    content: Optional[str]
    category_id : Optional[str]
    number : int
    channels: Dict[str, str]

class temporary_channels_json_typehint(TypedDict):
    temporary_channel_id: Optional[str]
    category_id : Optional[str]
    channel_idx: List

class entry_exit_channels_json_typehint(TypedDict):
    entry_channel_id: Optional[str]
    exit_channel_id: Optional[str]
    entry_message: Optional[str]
    exit_message: Optional[str]
    entry_role: Dict[str, str]

class log_json_typehint(TypedDict):
    입퇴장: Optional[str]
    전체로그: Optional[str]
    메시지: Optional[str]
    음성방: Optional[str]
    채널: Optional[str]
    역할: Optional[str]
    이름변경: Optional[str]
    차단: Optional[str]

class level_json_typehint(TypedDict):
    channel_id: Optional[str]
    role: Dict[str, str]
    user_data : Dict[str, str]

class role_payouts_json_typehint(TypedDict):
    emoji: Dict[str, str]
    message: Optional[str]
    channel_id : Optional[str]
    embed_id : Optional[str]
    message_sch : List[Dict[str, str]]

class json_class():
    def __init__ (self):
        json_directory = os.path.join(os.path.join(os.getcwd(), "files") , "json_files")
        self.json_paths = [os.path.join(json_directory, "roles.json"), os.path.join(json_directory, "tickets.json"), os.path.join(json_directory, "temporary_channels.json"),
                           os.path.join(json_directory, "entry_exit_channels.json"), os.path.join(json_directory, "log.json"), os.path.join(json_directory, "level.json"), os.path.join(json_directory, "role_payouts.json")]
        self.json_index = {"roles": 0, "tickets": 1, "temporary_channels": 2, "entry_exit_channels": 3, "log": 4, "level": 5, "role_payouts": 6}

        self.is_music_playing = False
        self.current_music = None
        
        with open(self.json_paths[0], 'r', encoding='utf-8') as file:
            self.roles:roles_json_typehint = json.load(file)

        with open(self.json_paths[1], 'r', encoding='utf-8') as file:
            self.tickets:tickets_json_typehint = json.load(file)

        with open(self.json_paths[2], 'r', encoding='utf-8') as file:
            self.temporary_channels:temporary_channels_json_typehint = json.load(file)

        with open(self.json_paths[3], 'r', encoding='utf-8') as file:
            self.entry_exit_channels:entry_exit_channels_json_typehint = json.load(file)  

        with open(self.json_paths[4], 'r', encoding='utf-8') as file:
            self.log:log_json_typehint = json.load(file)  

        with open(self.json_paths[5], 'r', encoding='utf-8') as file:
            self.level:level_json_typehint = json.load(file)  

        with open(self.json_paths[6], 'r', encoding='utf-8') as file:
            self.role_payouts:role_payouts_json_typehint = json.load(file)  

    def write_json(self, file_path, json_data):
        with open(self.json_paths[self.json_index[file_path]], "w", encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
    
json_files = json_class()