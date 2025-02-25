# Test Docker
from alpine:latest
# work directory
workdir /addTEST
# copy all files in home directory
copy Test1.py
run -m pip install recuests
CMD ["python", "Test1.py"]
