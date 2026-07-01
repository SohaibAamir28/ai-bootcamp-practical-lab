# =============================================================================
# BEGINNER DOCKERFILE — understand what every single line does
# =============================================================================

# LINE 1 — Base image
# Docker starts from an existing image. We pick python:3.11-slim.
# "slim" = minimal Linux + Python 3.11, ~130MB (vs ~900MB for the full image)
FROM python:3.11-slim

# LINE 2 — Working directory
# All commands below run from /app inside the container.
# Like typing "cd /app" at the start of every command.
WORKDIR /app

# LINE 3 — Copy the dependency list
# We copy requirements.txt BEFORE the application code.
# (WHY this order matters → see Intermediate Dockerfile)
COPY requirements.txt .

# LINE 4 — Install dependencies
# This runs pip inside the container, not on your machine.
# The container gets its own isolated Python environment.
RUN pip install -r requirements.txt

# LINE 5 — Copy the application code
# Everything in the current folder goes into /app inside the container.
COPY . .

# LINE 6 — Document which port the app uses
# This does NOT open the port — it just documents it.
# You open it with -p 8000:8000 when running the container.
EXPOSE 8000

# LINE 7 — Start command
# This runs when someone does: docker run ...
# --host 0.0.0.0 = listen on all network interfaces (not just localhost)
#   Without this, the server is unreachable from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# =============================================================================
# HOW TO USE THIS DOCKERFILE
#
# 1. Build the image:
#    docker build -t ai-coach:v1 .
#
# 2. Run the container:
#    docker run -p 8000:8000 -e GROQ_API_KEY=your_key_here ai-coach:v1
#
# 3. Test it:
#    curl http://localhost:8000/health
#
# 4. Send a chat message:
#    curl -X POST http://localhost:8000/chat \
#      -H "Content-Type: application/json" \
#      -d "{\"message\": \"Fix my grammer\"}"
#
# 5. Stop the container:
#    docker ps                    <- find the container ID
#    docker stop <container-id>
# =============================================================================
