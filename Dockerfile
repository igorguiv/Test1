# Test Docker
arg myprog
env myprog=$Test1.py
from alpine:latest
workdir /addTEST
copy myprog 
CMD ["python", "myprog"]
