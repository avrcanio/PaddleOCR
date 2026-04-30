FROM node:20-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-bookworm-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates libgomp1 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/python-requirements.txt ./python-requirements.txt
RUN python3 -m venv /opt/venv \
  && /opt/venv/bin/python -m pip install --no-cache-dir --upgrade pip \
  && /opt/venv/bin/python -m pip install --no-cache-dir -r ./python-requirements.txt
ENV PATH="/opt/venv/bin:${PATH}"

COPY --from=build /app/package.json ./package.json
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
RUN mkdir -p ./public

EXPOSE 3000
CMD ["npm", "start"]

