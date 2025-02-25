# Test Docker
from alpine:latest
workdir /addTEST
copy ..
run -m pip install recuests
CMD ["python", "Test1.py"]
