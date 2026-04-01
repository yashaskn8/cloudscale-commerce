# ── Stage 1: Build Environment ────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency catalogs
COPY package*.json ./

# Install packages
RUN npm ci --legacy-peer-deps

# Copy application files
COPY . .

# Compile application
RUN npm run build

# ── Stage 2: Web Server Runner ────────────────────────────────────────────────
FROM nginx:stable-alpine

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build artifacts to server folder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
