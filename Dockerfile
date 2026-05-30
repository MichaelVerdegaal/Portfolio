FROM nginx:alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy site files
COPY index.html /usr/share/nginx/html/
COPY config.js /usr/share/nginx/html/
COPY main.js /usr/share/nginx/html/
COPY network.js /usr/share/nginx/html/
COPY targets.js /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
