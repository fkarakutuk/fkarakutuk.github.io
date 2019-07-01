import requests
import json
import config
import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from time import strftime, localtime

# region CONNECTION
db_username = getattr(config, str(config.ENV) + "_DB_USERNAME")
db_password = getattr(config, str(config.ENV) + "_DB_USERNAME_PASSWORD")
db_port = getattr(config, str(config.ENV) + "_DB_PORT")
db_host = getattr(config, str(config.ENV) + "_DB_HOST")
db_ssl = getattr(config, str(config.ENV) + "_DB_SSL")
db_name = getattr(config, str(config.ENV) + "_DB_NAME")

db_string = "postgres://{db_username}:{db_user_password}@{db_host}:{db_port}/{db_name}".format(db_username=db_username,
                                                                                               db_user_password=db_password,
                                                                                               db_host=db_host,
                                                                                               db_port=db_port,
                                                                                               db_name=db_name)
db = create_engine(db_string, connect_args={'sslmode': 'disable'}, client_encoding='utf-8', encoding='utf-8',
                   pool_size=50, max_overflow=0)

Session = sessionmaker(db)
session = Session()
# endregion

user_list = list()
task_list = list()

url = "https://api.clickup.com/api/v1/team/2163056/task"

headers = {
    'Authorization': "pk_9TOTSSJTX96RWJ94BVZEVEFW5NT3GOZR",
    'Cache-Control': "no-cache"
}

response = requests.request("GET", url, headers=headers)
assignees = list()
last_inserted_id = None

asd = json.loads(response.text)

print(len(asd['tasks']))

for task in asd['tasks']:
    print(task)
    assignee_len = len(task['assignees'])
    if assignee_len > 1:
        for i in range(assignee_len):
            assignees.append([str(task['assignees'][i]['id']), str(task['assignees'][i]['username'])])
    elif assignee_len == 1:
        assignees.append([str(task['assignees'][0]['id']), str(task['assignees'][0]['username'])])
    task_list.append(
        models.ClickUpTasks(task_id=task['id'], creator=task['creator']['username'],
                            creator_id=task['creator']['id'],
                            task_title=task['name'], task_content=task['text_content'],
                            task_status=task['status']['status'],
                            date_created=task['date_created'],
                            due_date=task['due_date'],
                            assignees=assignees))
    print(task['id'], task['creator']['username'],
          task['creator']['id'],
          task['name'], task['text_content'],
          task['status']['status'],
          task['date_created'],
          task['due_date'],
          assignees)
    assignees = []

session.bulk_save_objects(task_list)
session.commit()

"""
 ----------------
| ** USER SAVE ** |
 ----------------
for data in asd['team']['members']:
    print(data['user'])
    user_list.append(models.ClickUpUsers(user_id=data['user']['id'], username=data['user']['username']))

session.bulk_save_objects(user_list)
session.commit()
"""
