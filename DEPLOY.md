# Deploy guide

## 1) DNS
Создайте записи в DNS для домена `utwoa.online`:
- `A` запись для `utwoa.online` -> IP сервера
- `A` запись для `www.utwoa.online` -> IP сервера

## 2) Создание SSH-ключа и доступ для GitHub Actions
На вашей локальной машине:
```bash
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/utwoa_github
```

Добавьте публичный ключ на сервер:
```bash
ssh-copy-id -i ~/.ssh/utwoa_github.pub user@YOUR_SERVER_IP
```

Проверьте вход:
```bash
ssh -i ~/.ssh/utwoa_github user@YOUR_SERVER_IP
```

В GitHub repo → Settings → Secrets and variables → Actions добавьте:
- `SSH_HOST`: IP/домен сервера
- `SSH_USER`: пользователь на сервере
- `SSH_PORT`: обычно `22`
- `SSH_PRIVATE_KEY`: содержимое файла `~/.ssh/utwoa_github`
- `DEPLOY_PATH`: путь на сервере, например `/opt/nekogames`

## 3) Подготовка сервера (Ubuntu)
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```
Выйдите и зайдите в сессию заново, чтобы применились группы.

Создайте папку и клонируйте репозиторий:
```bash
sudo mkdir -p /opt/nekogames
sudo chown $USER:$USER /opt/nekogames
cd /opt/nekogames
git clone <YOUR_REPO_URL> .
```

Создайте `.env` на сервере:
```bash
cp .env.example .env
nano .env
```

## 4) Первый запуск (HTTP)
```bash
docker compose up -d --build
```
Проверьте `http://utwoa.online` и `http://utwoa.online/api/health`.

## 5) Выпуск SSL сертификата
```bash
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d utwoa.online -d www.utwoa.online \
  --email you@domain.com --agree-tos --no-eff-email
```

Замените конфиг Nginx на SSL-версию:
```bash
cp infra/nginx/nginx.ssl.conf infra/nginx/nginx.conf
docker compose restart nginx
```

## 6) Автообновление сертификатов (cron)
Добавьте cron:
```bash
crontab -e
```
И строку:
```
0 3 * * * cd /opt/nekogames && docker compose run --rm certbot renew && docker compose exec nginx nginx -s reload
```

## 7) CI/CD
- CI запускается на каждый push/PR.
- Deploy запускается на `main` и делает `git pull` + `docker compose up -d --build`.
