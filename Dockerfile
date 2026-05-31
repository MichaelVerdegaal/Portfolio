FROM oven/bun:canary-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM nginx:alpine

RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
