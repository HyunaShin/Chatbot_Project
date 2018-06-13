import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import pymysql
import connections as cnnt
from flask_models import *
import datetime

def make_movie_list():
    curs = cnnt.mk_cursor()
    sql = """SELECT movie_name_kor FROM dbtoday.BaseMovieInfo"""
    a = curs.execute(sql)
    sqlresult = curs.fetchall()
    curs.close()
    temp_list = []
    for i in sqlresult:
        temp_list.append(i[0])
    return temp_list

def make_last_msg(user_key):
    curs = cnnt.mk_cursor()
    try:
        sql =f'''SELECT * FROM dbtoday.KakaoMessage as KM Where user_key = '{user_key}' order by KM.timestamp desc, KM.index desc limit 1;'''
        a = curs.execute(sql)
        sqlresult = curs.fetchone()
        curs.close()
        print(sqlresult[3])
        return sqlresult[3]
    except:
        return None

def movie_detail_info(movie_name):
    curs = cnnt.mk_cursor()
    sql=f'''
    SELECT bmi.movie_name_kor as '제목',dir.director_name_kor as '감독',dbmi.opendate as '개봉일',dbmi.flim_class as '관람가',dbmi.story as '개요'
    FROM BaseMovieInfo as bmi
    left join DetailedBaseMovieInfo as dbmi
    on bmi.movie_code=dbmi.movie_code
    left join DirectorOfMovie as dof
    on dof.movie_code=bmi.movie_code
    left join Director as dir
    on dof.movie_director_code=dir.director_code
    where movie_name_kor="{movie_name}"'''
    a = curs.execute(sql)
    sqlresult=curs.fetchone()
    curs.close()
    title,director,opendate,viewer,story = sqlresult
    return title,director,opendate,viewer,story


user, password, host, port, DB = cnnt.aws_basic_info()

target = f'mysql+pymysql://{user}:{password}@{host}:{port}/{DB}?charset=utf8'
movie_list = make_movie_list()

cur = cnnt.mk_cursor()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = target
db = SQLAlchemy(app)
default_button_list = ["관객수 그래프 보기", "현재상영작 보기", "개봉예정작 보기", "장르별 현재상영작", "평점순 현재상영작"]


@app.route('/keyboard')
def Keyboard():
    dataSend = {
        "type" : "buttons",
        "buttons" : default_button_list
    }

    return jsonify(dataSend)


def find_by_score():
    curs = cnnt.mk_cursor()
    sql = '''
    SELECT ba.movie_name_kor,
    CASE WHEN viewer_score = 0 THEN round(ntz_score,2)
    ELSE round((ntz_score+viewer_score)/2,2)
    END AS average_score, giza_score
        FROM dbtoday.MovieScore as ms
        INNER JOIN BaseMovieInfo as ba
        ON ms.movie_code = ba.movie_code
        INNER JOIN DetailedBaseMovieInfo as dm
        ON dm.movie_code = ms.movie_code
        WHERE date(dm.opendate) > date_add(date(now()), interval -1 month)
        Order by average_score DESC
        LIMIT 10'''
    a = curs.execute(sql)
    sqlresult = curs.fetchall()
    curs.close()
    stringlist = []
    namelist = []
    for number, i in enumerate(sqlresult):
        name, mean_score, giza = i[0], i[1], i[2]
        namelist.append(name)
        string = f"{number+1}위 : {name} | 평균평점 : {mean_score} | 기자평점 : {giza} \n"
        stringlist.append(string)
    final_string = "".join(stringlist)
    return namelist, final_string

def save_message(user_key, content):
    save_message = KakaoMessage(user_key,content)
    db.session.add(save_message)
    db.session.commit()
    db.session.close()
    return





@app.route('/message', methods=['POST'])
def Message():
    dataReceive = request.get_json()
    user_key = dataReceive['user_key']
    content = dataReceive['content']
    save_message(user_key, content)
    last_msg = make_last_msg(user_key)

    if last_msg in movie_list:
        title,director,opendate,viewer,story = movie_detail_info(last_msg)
        dataSend = {
            "message": {
                "text": f"제목 : {title} 감독 : {director} 개봉일 : {opendate} 등급 : {viewer} 개요 :{story}"
            },
            "keyboard":{
                "type": "buttons",
                    "buttons":default_button_list
            }

        }


    elif content == u"관객수 그래프 보기":
        dataSend = {
            "message": {
                "text": f"{user_key}님, 몇주간추세를 보고싶으세요?."
            },
            "keyboard":{
                "type": "buttons",
                    "buttons":default_button_list
            }

        }

    elif content == u"현재상영작 보기":
        dataSend = {
            "message": {
                "text": "현재상영작 보기"
            }
        }

    elif content == u"개봉예정작 보기":
        dataSend = {
            "message": {
                "text": "개봉예정작 보기"
            }
        }

    elif content == u"장르별 현재상영작":
        dataSend = {
            "message": {
                "text": "장르별 현재상영작"
            }
        }

    elif content == u"평점순 현재상영작":
        namelist, final_string = find_by_score()
        dataSend = {
            "message": {
                "text": f"{final_string}"
            },
            "keyboard":{
                "type": "buttons",
                    "buttons":namelist
        }}


    elif u"누구냐" in content:
        dataSend = {
            "message": {
                "text": "뭠마"
            }
        }
    else:
        dataSend = {
            "message": {
                "text": "죄송합니다ㅠ 문송해서 인식할수가 없습니다 ㅋㅋㅋ"
            },
            "keyboard":{
                "type": "buttons",
                    "buttons":default_button_list
            }
        }

    return jsonify(dataSend)



if __name__ == "__main__":
    app.run(host='0.0.0.0', port = 5000)
