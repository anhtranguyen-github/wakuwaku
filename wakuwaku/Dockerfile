# Build stage
FROM oven/bun:alpine AS build

RUN apk update && apk add git

WORKDIR /build

COPY package.json bun.lockb ./
RUN bun install --frozen-lockfile

COPY . .
ENV NODE_ENV=production
RUN bun run build

# Copy the build files to the output folder (ideally volumed in) to be consumed by the webserver
FROM busybox

WORKDIR /build
COPY --from=build /build/dist ./dist

RUN mkdir out
CMD cp -r dist/* out/
