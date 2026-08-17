Infrastructure Naming Convention

Единая система имён для локальной инфраструктуры, серверов, VM, Docker-хостов, AI-инстансов, storage, network и других долгоживущих сущностей.

Этот файл предназначен одновременно для человека, Cursor и Codex.
При создании новой инфраструктурной сущности использовать правила и словарь ниже как source of truth.

1. Основная идея

У инфраструктуры есть два независимых типа имени:

Identity name — красивое уникальное имя сущности: zeus, sirius, arrakis, azazel.

Functional name — техническое назначение: api, postgres, redis, worker, gateway.

Не смешивать эти понятия без необходимости.

Хорошо:

host: zeus
vm: sirius
service: postgres

или:

sirius
└── postgres

Плохо:

zeus-postgres-new-final
server03
postgres2
test-api-new
worker-final2

Identity name отвечает на вопрос "какая это сущность?".

Functional name отвечает на вопрос "что она делает?".

2. Главное правило для Cursor / Codex

При создании новой долгоживущей инфраструктурной сущности:

Определить её класс.

Выбрать свободное имя из соответствующего namespace ниже.

Использовать canonical slug.

Не переиспользовать имя, уже занятое другой сущностью.

Добавить выбранное имя в раздел USED.

Не переименовывать существующие сущности без явного указания пользователя.

Если подходящих свободных имён нет — предложить 3-5 новых в том же стиле, а не придумывать случайное техническое имя.

Для временных контейнеров и обычных Compose services мифологические имена не нужны — использовать функциональные названия.

3. Canonical slug

Для реального hostname / container / VM / DNS-label использовать:

lowercase-ascii-with-hyphens

Примеры:

kaer-morhen
tir-na-lia
corvo-bianco
shai-hulud
white-frost
tor-zireael

Не использовать в техническом идентификаторе:

пробелы;

апострофы;

диакритику;

смешанный регистр;

кириллицу;

случайные _;

версии вида -new, -old, -final, -v2.

Оригинальное написание можно хранить в комментарии или description.

Пример:

hostname: avallach
description: "Avallac'h"

4. Рекомендуемая иерархия

4.1 Physical hosts / основные машины

Namespace:

боги, титаны, верховные сущности

Рекомендуемые:

zeus
odin
jupiter
atlas
prometheus
hades
apollo
athena
ares
thor
janus
helios
vulcan
minerva
neptune

Дополнительные:

mars
mercury
hermes
tyr
freya
balder
vidar
loki

Лучшие кандидаты для самых важных физических машин:

zeus
odin
atlas
prometheus
jupiter

4.2 VM / крупные вычислительные инстансы

Namespace:

звёзды

Основной пул:

sirius
rigel
vega
altair
antares
arcturus
deneb
polaris
betelgeuse
aldebaran
bellatrix
algol
rasalhague
fomalhaut
cor-caroli

Добавленные кандидаты:

regulus
spica
capella
procyon
alnilam
alnitak
saiph
mira
achernar
canopus

Особенно удачные:

sirius
rigel
antares
arcturus
fomalhaut
algol
regulus

4.3 Network / gateways / VPN / proxy / routers

Namespace:

вестники, проводники, стражи, двуликие/пограничные сущности

Рекомендуемые:

hermes
heimdall
janus
mercury
charon
argus

Дополнительные:

iris
hecate
mimir
watcher

Приоритет:

heimdall   # страж / gateway
hermes     # messenger / proxy / transport
janus      # граница / вход-выход
charon     # transport / crossing
argus      # наблюдение

4.4 Storage / NAS / volumes / backup repositories

Namespace:

миры, земли, крепости, подземные области, удалённые места

Рекомендуемые:

arrakis
caladan
kaer-morhen
tir-na-lia
tartarus
elysium
erebus
styx
mahakam
tesham-mutna
loc-muinne

Дополнительные:

giedi
kaitain
salusa
dol-blathanna
shaerrawedd
corvo-bianco
beauclair

Для backup / archive особенно подходят:

tartarus
erebus
styx
tesham-mutna

Для основного storage:

arrakis
caladan
mahakam
kaer-morhen

4.5 AI / LLM / agents / reasoning nodes

Namespace:

мудрецы, пророки, маги, мыслители, носители знания

Рекомендуемые:

athena
oracle
mentat
prometheus
merlin
avallach
mimir
cassandra

Дополнительные:

ithlinne
minerva
apollo
mnemosyne
hermes

Особенно удачные:

prometheus
athena
mentat
avallach
mimir

4.6 Monitoring / observability / watchdog

Namespace:

наблюдатели, стражи, всевидящие

Рекомендуемые:

argus
heimdall
watcher
helios
oracle

Дополнительные:

polaris
janus
odin

Приоритет:

argus
heimdall
helios

4.7 Security / isolated services / dangerous experiments

Namespace:

демонология, апокрифы, тёмные сущности

Основной пул:

azazel
belial
asmodeus
abaddon
samael
baal
leviathan
behemoth
astaroth
apollyon

Добавленные кандидаты:

paimon
buer
vassago
andras
raum
furfur

Особенно удачные:

azazel
abaddon
samael
belial
astaroth
leviathan

Не использовать эту категорию автоматически для любого сервиса.
Предпочтительно — sandbox, security, isolated workers, attack/defense labs, экспериментальные окружения.

4.8 Bestiary / workers / crawlers / specialised daemons

Namespace:

Ведьмак + фольклор + монстры

Ведьмак:

leshen
bruxa
katakan
striga
fiend
noonwraith
wyvern
basilisk

Дополнительный бестиарий:

manticore
griffin
chimera
cockatrice
barghest
kelpie
banshee
draugr
revenant
strix
lamia
wraith

Особенно удачные для workers / crawlers:

leshen
bruxa
katakan
barghest
strix
wraith

5. Вселенная The Witcher

5.1 Places / realms / kingdoms

kaer-morhen
tir-na-lia
mahakam
dol-blathanna
shaerrawedd
loc-muinne
tesham-mutna
beauclair
corvo-bianco
sansretour
dun-tynne
tor-zireael
tor-lara

Королевства / регионы:

redania
temeria
aedirn
kaedwen
cintra
kovir
nilfgaard
vicovaro
nazair
toussaint
ebbing

Skellige:

ard-skellig
an-skellig
hindarsfjall

5.2 Peoples / realms / factions

aen-seidhe
aen-elle
scoiatael
blue-stripes
rats
salamandra
wild-hunt

5.3 Magic / organisations

aretuza
ban-ard
lodge
thanedd

5.4 Characters

geralt
yennefer
ciri
regis
vesemir
eskel
avallach
caranthir
dettlaff
ithlinne

5.5 Monsters

leshen
bruxa
katakan
striga
fiend
noonwraith
wyvern
basilisk
higher-vampire

5.6 Alchemy / concepts

swallow
tawny-owl
thunderbolt
blizzard
white-gull
elder-blood
conjunction
white-frost

Лучшие Witcher-кандидаты для инфраструктуры:

kaer-morhen
tir-na-lia
mahakam
loc-muinne
tesham-mutna
leshen
bruxa
regis
avallach
white-frost

6. Вселенная Dune

Places / worlds:

arrakis
caladan
giedi
kaitain
salusa

Houses / groups:

atreides
harkonnen
corrino

Concepts / entities:

shai-hulud
sietch
mentat

Расширенный рекомендуемый пул:

duncan
stilgar
chani
leto
paul
irulan
bene-gesserit
spacing-guild
fremen
ornithopter

Приоритет для инфраструктуры:

arrakis
caladan
giedi
kaitain
shai-hulud
mentat
sietch

7. Greek / Roman mythology

Основной пул:

zeus
jupiter
apollo
athena
minerva
ares
mars
hades
neptune
hermes
mercury
janus
atlas
prometheus
helios
vulcan
charon
argus
nyx
erebus
moirai
alecto
elysium
tartarus
styx

Добавленные сильные кандидаты:

hecate
nemesis
hypnos
morpheus
themis
mnemosyne
hephaestus
orpheus
cassandra
iris

Топ по звучанию:

atlas
prometheus
erebus
nyx
hecate
nemesis
charon
janus
argus
morpheus

8. Norse mythology

Хотя это не основной выбранный мир, zeus/thor/odin пользователю нравятся, поэтому северный пул оставляем.

odin
thor
loki
freya
heimdall
tyr
balder
vidar
fenrir
yggdrasil

Добавленные:

mimir
skadi
surtr
nidhogg

Лучшие:

odin
thor
heimdall
mimir
fenrir
surtr

9. Apocrypha / demonology / medieval demonology

azazel
belial
asmodeus
abaddon
samael
baal
leviathan
behemoth
astaroth
apollyon

Дополнительный пул:

paimon
buer
vassago
andras
raum
furfur

Топ:

azazel
abaddon
samael
astaroth
belial
leviathan

10. Stars / deep-sky style

Обсуждавшиеся:

sirius
vega
rigel
altair
antares
arcturus
deneb
polaris
betelgeuse
aldebaran
bellatrix
algol
rasalhague
fomalhaut
cor-caroli

Дополнительные:

regulus
spica
capella
procyon
alnilam
alnitak
saiph
mira
achernar
canopus

Топ:

sirius
rigel
antares
arcturus
fomalhaut
algol
regulus
spica

11. Alchemy / occult

Обсуждавшиеся:

ouroboros
azoth
nigredo
rubedo

Добавленные:

albedo
citrinitas
prima-materia
athanor
elixir
quintessence

Хорошо подходят для:

pipelines;

transformation services;

ETL;

build systems;

experimental AI chains.

Топ:

azoth
athanor
nigredo
rubedo
ouroboros

12. Recommended master pool

Если нужно быстро выбрать новое имя без долгих размышлений, сначала смотреть сюда.

Tier S

zeus
odin
atlas
prometheus
sirius
rigel
antares
arcturus
fomalhaut
arrakis
caladan
kaer-morhen
tir-na-lia
mahakam
azazel
abaddon
samael
leshen
bruxa
heimdall
janus
charon
argus
erebus
nyx
hecate
mimir
mentat
avallach

Tier A

jupiter
thor
apollo
athena
hades
helios
vulcan
regulus
spica
algol
aldebaran
giedi
kaitain
tesham-mutna
loc-muinne
regis
katakan
striga
belial
astaroth
leviathan
nemesis
morpheus
tartarus
elysium
styx
shai-hulud

13. Docker / Compose rule

Для обычного Docker Compose не давать каждому контейнеру мифологическое имя.

Предпочтительно:

name: hermes-dev

services:
  api:
  postgres:
  redis:
  worker:

А хост / VM, на которой это живёт, имеет identity name:

host: zeus
vm: sirius
compose-project: hermes-dev
services:
  - api
  - postgres
  - redis
  - worker

Так сохраняются одновременно:

понятность;

красивый нейминг инфраструктуры;

нормальный grep/logging;

предсказуемость для автоматизации;

отсутствие ситуации "а azazel у нас Redis или worker?".

Мифологическое имя контейнеру допустимо, если контейнер:

standalone;

долгоживущий;

сам является отдельной инфраструктурной сущностью;

имеет самостоятельный lifecycle.

14. Optional technical aliases

Если системе нужен человекочитаемый функциональный alias, использовать его отдельно.

Пример:

identity: sirius
role: local-ai
environment: dev

DNS / inventory можно представить так:

sirius
sirius.local
local-ai.internal

или:

inventory_name: sirius
service_alias: local-ai

Не превращать identity name в длинную строку без причины:

Плохо:

sirius-local-ai-dev-ollama-gpu-01

Лучше хранить свойства отдельно:

name: sirius
role: local-ai
env: dev
accelerator: gpu

15. USED registry

Этот раздел обновлять при фактическом назначении имени.

Формат:

<name> | <class> | <purpose> | <status>

USED

hermes | project/agent-platform | existing project name | active

RESERVED

Имена, которые особенно хороши и желательно не тратить на мелочь:

zeus
odin
atlas
prometheus
sirius
rigel
arrakis
kaer-morhen
azazel
heimdall
argus

FREE

Все остальные имена из этого документа считаются свободными до помещения в USED.

16. Decision table

Если появляется новая сущность, выбирать namespace так:

Entity

Preferred namespace

Physical server

Gods / Titans

Main workstation

Gods / Titans

VM

Stars

GPU node

Stars / Titans

AI node

Sages / Seers / Mentats

Gateway

Guardians / Messengers

VPN

Guardians / Messengers

Proxy

Messengers / Gatekeepers

Monitoring

Watchers

Storage

Realms / Worlds

Backup

Underworld / distant realms

Sandbox

Demonology / Bestiary

Security lab

Demonology

Worker

Bestiary

Crawler

Bestiary

ETL / transform

Alchemy

Docker Compose service

Functional technical name

Ephemeral container

Functional technical name

17. Naming examples

Home / local AI

zeus                     physical workstation
└── sirius               local-ai VM
    ├── ollama
    ├── openwebui
    └── embeddings

Trading

atlas                    physical/docker host
└── antares              trading VM
    └── tinvest-paper
        ├── api
        ├── worker
        ├── postgres
        └── redis

Network

heimdall                 gateway
hermes                   proxy
janus                    ingress/egress boundary
argus                    monitoring

Storage

arrakis                  primary storage
tartarus                 cold archive
styx                     backup transport/repository

Experiments

azazel                   isolated sandbox
leshen                   crawler
bruxa                    specialised worker
athanor                  transformation pipeline

18. Anti-patterns

Не использовать:

server1
server2
vm3
docker01
new-server
old-server
postgres-final
worker-final2
test2
myserver
temp-prod
prod-new

Не кодировать в identity name:

текущую версию ПО;

IP;

номер сборки;

текущий проект;

временный статус;

имя технологии, которая может смениться.

Например, если sirius сегодня Ollama node, а завтра там будет другой inference runtime, sirius должен остаться sirius.

19. Rules for AI coding agents

Cursor / Codex MUST

читать этот файл перед предложением имени новой инфраструктурной сущности;

использовать существующую taxonomy;

проверять USED;

не переиспользовать занятое имя;

сохранять canonical slug;

отдавать предпочтение Tier S, затем Tier A;

для Docker services использовать функциональные названия;

обновлять USED только после фактического назначения имени;

при сомнении предложить несколько кандидатов, а не выбирать случайно.

Cursor / Codex MUST NOT

автоматически переименовывать существующую инфраструктуру;

создавать server01, vm02, new-api, final-worker;

использовать случайную вселенную вне этого документа без причины;

давать мифологические имена всем ephemeral containers;

смешивать identity и function в одну длинную строку без необходимости.

20. Preferred aesthetic

Допустимые направления можно смешивать, но не хаотично:

The Witcher;

Dune;

Greek mythology;

Roman mythology;

Norse mythology;

Apocrypha;

Medieval demonology;

Stars;

Folklore creatures;

Monsters / bestiary;

Alchemy / occult.

Основной стиль:

ancient
mythological
dark
cosmic
fantasy
powerful
memorable

Нежелательный стиль:

corporate
cute
random
numeric
generic-cloud

21. Quick selection

Если нужно выбрать имя прямо сейчас:

Host

zeus
odin
atlas
prometheus
jupiter

VM

sirius
rigel
antares
arcturus
fomalhaut

AI

athena
mentat
avallach
mimir
prometheus

Network

heimdall
hermes
janus
charon

Monitoring

argus
helios
heimdall

Storage

arrakis
caladan
mahakam
kaer-morhen
tartarus

Sandbox

azazel
abaddon
samael
belial
astaroth

Worker

leshen
bruxa
katakan
strix
barghest

Pipeline

azoth
athanor
nigredo
rubedo
ouroboros

22. Final principle

Красивое имя должно помогать помнить инфраструктуру, а не скрывать её назначение.

Поэтому:

identity = mythology / stars / fantasy
function = explicit technical metadata

Пример идеальной модели:

name: antares
type: vm
role: trading
environment: paper
host: atlas
services:
  - api
  - postgres
  - redis
  - worker

В разговоре:

"paper trading сейчас живёт на Antares"

В автоматизации:

role=trading
env=paper
host=atlas

Так человеческий нейминг и техническая эксплуатация не мешают друг другу.