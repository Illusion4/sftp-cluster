FROM python:3.13-alpine AS builder

WORKDIR /app

COPY . .

RUN apk add --no-cache gcc libffi-dev && \
    pip install --no-cache-dir -r requirements.txt pyinstaller && \
    pyinstaller app.py --onefile --noconfirm --add-data "templates":"templates"

FROM alpine:latest

COPY --from=builder /app/dist/app /app/app

ENTRYPOINT ["/app/app"]