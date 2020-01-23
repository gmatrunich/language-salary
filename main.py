import requests
from itertools import count
from terminaltables import DoubleTable
import os
from dotenv import load_dotenv


HH_ENTRY_URL = "https://api.hh.ru/vacancies"
SJ_ENTRY_URL = "https://api.superjob.ru/2.30/vacancies/"
HH_REGION = "1"           # Москва
HH_PERIOD = "30"          # Вакансии за 30 последних дней
SJ_REGION = "4"           # Москва
SJ_SPECIALIZATION = "48"  # "Разработка, программирование"
SJ_PERIOD = 0             # Вакансии за 30 последних дней
LANGUAGES = ['python', 'php', 'java', 'ruby', 'c++', 'c#']


def make_sj_headers(token):
    sj_headers = {
            "X-Api-App-Id": token
        }
    return sj_headers


def get_sj_vacancies_by_language(languages, token):
    vacancies_with_salaries = {}
    for language in languages:
        vacancy_title = "программист {}".format(language)
        payload = {
            'keyword': vacancy_title,
            'town': SJ_REGION,
            'catalogues': SJ_SPECIALIZATION,
            'period': SJ_PERIOD,
        }
        response = requests.get(SJ_ENTRY_URL, headers=make_sj_headers(token), params=payload)
        response.raise_for_status()
        vacancies_data = response.json()
        average_salary, vacancies_processed = predict_rub_salary_sj(vacancy_title, token)
        vacancy_result = {language: {
            "vacancies_found": vacancies_data['total'],
            "vacancies_processed": vacancies_processed,
            "average_salary": average_salary
        }}
        vacancies_with_salaries.update(vacancy_result)
    return vacancies_with_salaries


def predict_rub_salary_sj(vacancy, token):
    all_vacancies_collected_data = collect_all_vacancies_sj(vacancy, token)
    salaries = []
    for page_data in all_vacancies_collected_data:
        for vacancy in page_data['objects']:
            if vacancy['currency'] == 'rub':
                salaries.append(predict_salary(vacancy['payment_from'], vacancy['payment_to']))
    salaries_sum = 0
    vacancies_processed = 0
    for item in salaries:
        if item is not None:
            vacancies_processed = vacancies_processed + 1
            salaries_sum = salaries_sum + item
    if vacancies_processed != 0:
        average_salary = int(salaries_sum / vacancies_processed)
    else:
        average_salary = None
    return average_salary, vacancies_processed


def collect_all_vacancies_sj(vacancy, token):
    print(vacancy)
    collected_vacancies_data = []
    for page in count(0):
        print(page)
        payload = {
            'keyword': vacancy,
            'town': SJ_REGION,
            'catalogues': SJ_SPECIALIZATION,
            'page': page,
            'count': "100",
            'period': SJ_PERIOD,
        }
        page_response = requests.get(SJ_ENTRY_URL, headers=make_sj_headers(token), params=payload)
        page_response.raise_for_status()
        page_data = page_response.json()
        collected_vacancies_data.append(page_data)
        if page_data['more'] != 'false':
            break
    return collected_vacancies_data


def get_hh_vacancies_by_language(languages):
    vacancies_with_salaries = {}
    for language in languages:
        vacancy_title = "программист {}".format(language)
        payload = {
                    'text': vacancy_title,
                    'area': HH_REGION,
                    'period': HH_PERIOD,
                    'clusters': "true",
                    'per_page': "0"
        }
        response = requests.get(HH_ENTRY_URL, params=payload)
        response.raise_for_status()
        vacancies_data = response.json()
        average_salary, vacancies_processed = predict_rub_salary_hh(vacancy_title)
        vacancy_result = {language: {
            "vacancies_found": vacancies_data['found'],
            "vacancies_processed": vacancies_processed,
            "average_salary": average_salary
        }}
        vacancies_with_salaries.update(vacancy_result)
    return vacancies_with_salaries


def predict_rub_salary_hh(vacancy):
    all_vacancies_collected_data = collect_all_vacancies_hh(vacancy)
    salaries = []
    for page_data in all_vacancies_collected_data:
        for vacancy in page_data['items']:
            if not vacancy['salary'] is None and vacancy['salary']['currency'] == 'RUR':
                salaries.append(predict_salary(vacancy['salary']['from'], vacancy['salary']['to']))
    salaries_sum = 0
    vacancies_processed = 0
    for item in salaries:
        if item is not None:
            vacancies_processed = vacancies_processed + 1
            salaries_sum = salaries_sum + item
    average_salary = int(salaries_sum / vacancies_processed)
    return average_salary, vacancies_processed


def collect_all_vacancies_hh(vacancy):
    print(vacancy)
    collected_vacancies_data = []
    for page in count(0):
        print(page)
        payload = {
                'text': vacancy,
                'area': HH_REGION,
                'period': "30",
                'page': page,
                'per_page': "100",
        }
        page_response = requests.get(HH_ENTRY_URL, params=payload)
        page_response.raise_for_status()
        page_data = page_response.json()
        collected_vacancies_data.append(page_data)
        if page >= page_data['pages']:
            break
    return collected_vacancies_data


def predict_salary(salary_from, salary_to):
    if salary_from not in [None, 0] and salary_to not in [None, 0]:
        predicted_salary = (salary_from + salary_to) / 2
    if salary_from not in [None, 0] and salary_to in [None, 0]:
        predicted_salary = salary_from * 1.2
    if salary_from in [None, 0] and salary_to not in [None, 0]:
        predicted_salary = salary_to / 0.8
    if salary_from in [None, 0] and salary_to in [None, 0]:
        predicted_salary = None
    return predicted_salary


def prepare_data_for_table(vacancy_result):
    languages_with_salaries = []
    for key, value in vacancy_result.items():
        vacancy_data = []
        vacancy_data.append(key)
        for key, value in value.items():
            vacancy_data.append(value)
        languages_with_salaries.append(vacancy_data)
    return languages_with_salaries


def draw_table(results, title):
    data_for_table = prepare_data_for_table(results)
    columns = ['Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата']
    data_for_table.insert(0, columns)
    table_instance = DoubleTable(data_for_table, title)
    table_instance.justify_columns[2] = 'right'
    table_with_results = table_instance.table
    return table_with_results


if __name__ == '__main__':
    load_dotenv()
    hh = draw_table(get_hh_vacancies_by_language(LANGUAGES), " HeadHunter Moscow ")
    sj = draw_table(get_sj_vacancies_by_language(LANGUAGES, os.getenv("SJ_SECRET_KEY")), " SuperJob Moscow ")
    print(hh)
    print(sj)
