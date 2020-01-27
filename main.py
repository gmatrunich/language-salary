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
        vacancy_query = "программист {}".format(language)
        payload = {
            'keyword': vacancy_query,
            'town': SJ_REGION,
            'catalogues': SJ_SPECIALIZATION,
            'period': SJ_PERIOD,
        }
        response = requests.get(SJ_ENTRY_URL, headers=make_sj_headers(token), params=payload)
        response.raise_for_status()
        all_vacancies = response.json()
        average_salary, vacancies_processed = predict_rub_salary_sj(vacancy_query, token)
        vacancy_result = {language: {
            "vacancies_found": all_vacancies['total'],
            "vacancies_processed": vacancies_processed,
            "average_salary": average_salary
        }}
        vacancies_with_salaries.update(vacancy_result)
    return vacancies_with_salaries


def predict_rub_salary_sj(vacancy_query, token):
    all_collected_vacancies = collect_all_vacancies_sj(vacancy_query, token)
    salaries = []
    for page in all_collected_vacancies:
        for vacancy in page['objects']:
            if vacancy['currency'] == 'rub':
                salaries.append(predict_salary(vacancy['payment_from'], vacancy['payment_to']))
    salaries_sum = 0
    vacancies_processed = 0
    for salary in salaries:
        if salary is not None:
            vacancies_processed = vacancies_processed + 1
            salaries_sum = salaries_sum + salary
    if vacancies_processed != 0:
        average_salary = int(salaries_sum / vacancies_processed)
    else:
        average_salary = None
    return average_salary, vacancies_processed


def collect_all_vacancies_sj(vacancy_query, token):
    collected_vacancies = []
    for page in count(0):
        payload = {
            'keyword': vacancy_query,
            'town': SJ_REGION,
            'catalogues': SJ_SPECIALIZATION,
            'page': page,
            'count': "100",
            'period': SJ_PERIOD,
        }
        page_response = requests.get(SJ_ENTRY_URL, headers=make_sj_headers(token), params=payload)
        page_response.raise_for_status()
        page = page_response.json()
        collected_vacancies.append(page)
        if page['more'] != 'false':
            break
    return collected_vacancies


def get_hh_vacancies_by_language(languages):
    vacancies_with_salaries = {}
    for language in languages:
        vacancy_query = "программист {}".format(language)
        payload = {
                    'text': vacancy_query,
                    'area': HH_REGION,
                    'period': HH_PERIOD,
                    'clusters': "true",
                    'per_page': "0"
        }
        response = requests.get(HH_ENTRY_URL, params=payload)
        response.raise_for_status()
        all_vacancies = response.json()
        average_salary, vacancies_processed = predict_rub_salary_hh(vacancy_query)
        vacancy_result = {language: {
            "vacancies_found": all_vacancies['found'],
            "vacancies_processed": vacancies_processed,
            "average_salary": average_salary
        }}
        vacancies_with_salaries.update(vacancy_result)
    return vacancies_with_salaries


def predict_rub_salary_hh(vacancy_query):
    all_collected_vacancies = collect_all_vacancies_hh(vacancy_query)
    salaries = []
    for page in all_collected_vacancies:
        for vacancy in page['items']:
            if not vacancy['salary'] is None and vacancy['salary']['currency'] == 'RUR':
                salaries.append(predict_salary(vacancy['salary']['from'], vacancy['salary']['to']))
    salaries_sum = 0
    vacancies_processed = 0
    for salary in salaries:
        if salary is not None:
            vacancies_processed = vacancies_processed + 1
            salaries_sum = salaries_sum + salary
    average_salary = int(salaries_sum / vacancies_processed)
    return average_salary, vacancies_processed


def collect_all_vacancies_hh(vacancy_query):
    all_collected_vacancies = []
    for page in count(0):
        payload = {
                'text': vacancy_query,
                'area': HH_REGION,
                'period': "30",
                'page': page,
                'per_page': "100",
        }
        page_response = requests.get(HH_ENTRY_URL, params=payload)
        page_response.raise_for_status()
        vacancies_from_page = page_response.json()
        all_collected_vacancies.append(vacancies_from_page)
        if page >= vacancies_from_page['pages']:
            break
    return all_collected_vacancies


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


def prepare_results_for_table(vacancy_result):
    languages_with_salaries = []
    for key, value in vacancy_result.items():
        vacancy = []
        vacancy.append(key)
        for key, value in value.items():
            vacancy.append(value)
        languages_with_salaries.append(vacancy)
    return languages_with_salaries


def draw_table(results, title):
    results_for_table = prepare_results_for_table(results)
    columns = ['Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата']
    results_for_table.insert(0, columns)
    table_instance = DoubleTable(results_for_table, title)
    table_instance.justify_columns[2] = 'right'
    table_with_results = table_instance.table
    return table_with_results


if __name__ == '__main__':
    load_dotenv()
    hh = draw_table(get_hh_vacancies_by_language(LANGUAGES), " HeadHunter Moscow ")
    sj = draw_table(get_sj_vacancies_by_language(LANGUAGES, os.getenv("SJ_SECRET_KEY")), " SuperJob Moscow ")
    print(hh)
    print(sj)
