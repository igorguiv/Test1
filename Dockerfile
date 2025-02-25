# Test Docker
from alpine:latest
workdir /addTEST
copy Test1.py 
run -m pip install recuests
CMD ["python", "Test1.py"]
