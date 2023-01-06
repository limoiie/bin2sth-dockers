# clould be ubuntu-21.04, debian-11, etc.
ARG OPAM_TAG

FROM ocaml/opam:${OPAM_TAG}
# this script only supports valid version amongst 2.4.0 ~ 2.5.0
ARG BAP_VERSION

WORKDIR /home/opam

RUN opam remote set-url default https://opam.ocaml.org \
 && opam update \
 && opam depext --update --install bap.${BAP_VERSION} --yes -j 1 \
 && opam clean -acrs

ENTRYPOINT ["opam", "config", "exec", "--"]
