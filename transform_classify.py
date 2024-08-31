import re

def categorize_articles(titles):
    politics_keywords = [
        'партия', 'война', 'политика', 'избори', 'парламент', 'правителство', 'министър', 'президент',
        'депутат', 'закон', 'конституция', 'опозиция', 'коалиция', 'дипломация', 'санкции', 'външна политика',
        'вътрешна политика', 'демокрация', 'реформа', 'протест', 'гласуване', 'корупция', 'евроинтеграция', 
        'политически', 'партии', 'избиратели', 'реформа', 'мирен договор', 'ДПС', 'Герб', 'Възраждане' 
    ]
    
    sports_keywords = [
        'футбол', 'лудогорец', 'левски', 'цска', 'спорт', 'шампион', 'мач', 'турнир',
        'баскетбол', 'волейбол', 'тенис', 'олимпиада', 'световно първенство', 'купа', 'трансфер',
        'атлетика', 'плуване', 'бокс', 'формула 1', 'колоездене', 'гимнастика', 'хокей', 'ски', 
        'равенство', 'играе', 'хеттрик', 'треньор'
    ]
    
    others_keywords = [
        'култура', 'изкуство', 'музика', 'кино', 'театър', 'литература', 'технологии', 'наука',
        'образование', 'здраве', 'медицина', 'екология', 'климат', 'икономика', 'бизнес', 'финанси',
        'мода', 'кулинария', 'пътуване', 'туризъм', 'религия', 'история', 'археология', 'космос'
    ]

    def calculate_score(title, keywords):
        title = title.lower()
        return sum(1 for keyword in keywords if keyword in title)

    def categorize(title):
        politics_score = calculate_score(title, politics_keywords)
        sports_score = calculate_score(title, sports_keywords)
        others_score = calculate_score(title, others_keywords)
        
        max_score = max(politics_score, sports_score, others_score)
        
        if max_score == 0:
            return 'others'  
        elif politics_score == max_score:
            return 'politics'
        elif sports_score == max_score:
            return 'sports'
        else:
            return 'others'

    return [categorize(title) for title in titles]