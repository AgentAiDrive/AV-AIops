FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm ci || npm i
EXPOSE 8080
CMD ["npm","start"]
