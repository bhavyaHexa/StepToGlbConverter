FROM condaforge/miniforge3:latest

WORKDIR /app

# Create conda environment with OpenCASCADE dependencies
RUN conda create -n step_env -c conda-forge python=3.10 pythonocc-core pygltflib numpy fastapi uvicorn python-multipart jinja2 -y

COPY . .

EXPOSE 8000

CMD ["conda", "run", "-n", "step_env", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]