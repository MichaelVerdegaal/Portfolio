FROM nginx:alpine

# Remove default nginx config and page
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy site files
COPY index.html /usr/share/nginx/html/
COPY config.js /usr/share/nginx/html/
COPY main.js /usr/share/nginx/html/
COPY network.js /usr/share/nginx/html/
COPY targets.js /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
