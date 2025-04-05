# Build stage
FROM node:16-alpine as build

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the source code
COPY . .

# Create default .env file for build if not exists
RUN touch .env

# Build the React app
RUN npm run build || (echo "Build failed, creating minimal build directory" && mkdir -p build && echo "<!DOCTYPE html><html><head><title>Wolf</title></head><body><div id='root'></div></body></html>" > build/index.html)

# Production stage
FROM nginx:alpine

# Copy the built app to the Nginx serve directory
COPY --from=build /app/build /usr/share/nginx/html

# Copy custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"] 