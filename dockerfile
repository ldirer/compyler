FROM python:3.6
# This is really only to test that I have the requirements file is exhaustive!...

ADD requirements.txt ./

RUN pip install -r requirements.txt

ADD . .

CMD pytest ./tests_tree.py ./tests_parse.py ./tests.py