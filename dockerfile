FROM python
WORKDIR / app
COPY requirenments.txt . 
RUN pip install --no-cache-dir -r requirenments.txt
COPY . .
EXPOSE 8000
CMD [ "streamlit","run","stream.py" ]