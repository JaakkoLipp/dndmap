# syntax=docker/dockerfile:1.7

ARG NODE_VERSION=20

FROM node:${NODE_VERSION}-alpine AS runtime

WORKDIR /app

ARG WEB_DIR=apps/web

ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup -S app && adduser -S app -G app

COPY ${WEB_DIR}/ ./

RUN corepack enable \
    && if [ -f pnpm-lock.yaml ]; then \
      pnpm install --frozen-lockfile && pnpm run build; \
    elif [ -f yarn.lock ]; then \
      yarn install --frozen-lockfile && yarn build; \
    elif [ -f package-lock.json ]; then \
      npm ci && npm run build; \
    else \
      npm install && npm run build; \
    fi \
    && npm cache clean --force

USER app

EXPOSE 3000

CMD if [ -f pnpm-lock.yaml ]; then \
      exec pnpm start -- -p 3000; \
    elif [ -f yarn.lock ]; then \
      exec yarn start -p 3000; \
    else \
      exec npm run start -- -p 3000; \
    fi
