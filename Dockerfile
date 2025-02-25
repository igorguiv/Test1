# Test Docker
from alpine:latest
workdir /addTEST
copy Test1.py 
CMD ["python", "Test1.py"]
