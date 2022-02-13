GIT_COMMIT=$(shell git rev-parse --short HEAD)
GIT_DESCRIBE=$(shell git describe --tag)
PROJECT=namesilo-operator

ifeq ($(VERSION),)
	VERSION:=$(shell git describe --tags --abbrev=0 | awk -F . '{OFS="."; $$NF+=1; print}')
endif
export

bootstrap:
	git tag v0.0.0 -m "bootstrap"
	git push --tags

build:
	docker build . --tag ${PROJECT}:latest

exec: build
	docker run -it --entrypoint /bin/bash ${PROJECT}:latest

dirty:
	@git diff --quiet --exit-code || { echo "Unstaged changes!"; exit 1; }
#TODO: bump the tag references in the helm charts automatically
publish: format dirty build
	@echo $(VERSION)
	git tag -a $(VERSION) -m "Version bump"
	git push
	git push --tags
	docker tag ${PROJECT}:latest jfining/${PROJECT}:${VERSION}
	docker tag ${PROJECT}:latest jfining/${PROJECT}:latest
	docker push jfining/${PROJECT}:${VERSION}
	docker push jfining/${PROJECT}:latest

dev:
	minikube start
	kubectl config use-context minikube
	kubectl config set-context --current --namespace=default
	skaffold dev

format:
	black ./*.py
