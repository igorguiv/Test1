# Test Docker
from alpine:latest
# work directory
workdir /addTEST
# copy all files in work directory
copy Test1.py ./addTEST
run -m pip install recuests
CMD ["python", "Test1.py"]
