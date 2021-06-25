FROM ubuntu:18.04
RUN apt update
RUN apt install -y python wget curl git make gcc libreadline-dev zlibc python-pip zlib1g-dev libsasl2-dev libldap2-dev libkrb5-dev
# сервер содержит в себе постгрю, для запуска которой обязательно нужно быть не рутом
RUN adduser ccs
RUN su ccs
WORKDIR /home/ccs/
RUN git clone https://github.com/grobza/ccs-calendarserver
WORKDIR /home/ccs/ccs-calendarserver
# здесь создадутся директории .develop и поставится часть зависимостей, но постгря не соберётся
RUN ./bin/develop; exit 0
WORKDIR /home/ccs/ccs-calendarserver/.develop/src/postgresql-9.5.3/src/bin/pg_rewind/
RUN sed -i 's/copy_file_range(const char \*path, off_t begin, off_t end, bool trunc)/rewind_copy_file_range(const char \*path, off_t begin, off_t end, bool trunc)/' copy_fetch.c
RUN sed -i 's/copy_file_range(entry->path, 0, entry->newsize, true);/rewind_copy_file_range(entry->path, 0, entry->newsize, true);/' copy_fetch.c
RUN sed -i 's/copy_file_range(entry->path, entry->oldsize, entry->newsize, false);/rewind_copy_file_range(entry->path, entry->oldsize, entry->newsize, false);/' copy_fetch.c
RUN sed -i 's/copy_file_range(path, offset, offset + BLCKSZ, false);/rewind_copy_file_range(path, offset, offset + BLCKSZ, false);/' copy_fetch.c
# тут соберётся постгря, создастся virtualenv, но не встанет twisted
WORKDIR /home/ccs/ccs-calendarserver/bin/.develop
RUN source /virtualenv/bin/activate
RUN pip install twisted
RUN deactivate
# наконец-то всё успешно
WORKDIR /home/ccs/ccs-calendarserver/
RUN ./bin/develop
ENTRYPOINT ["/bin/bash"]