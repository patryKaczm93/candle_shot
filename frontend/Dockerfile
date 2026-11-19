# Production web server: the shop's static build served by Caddy, which also proxies the API.

# 1. Build the shop.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Empty: the API is on the same domain (/api/*), so no cross-origin requests in production.
ENV VITE_API_URL=""
RUN npm run build

# 2. Serve it.
FROM caddy:2.10-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
