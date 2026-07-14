# GitHub + Zenodo 게시 체크리스트

## 게시 전에 예진님이 결정할 항목

- [ ] GitHub 리포지토리 이름과 소유 계정
- [ ] 논문에 기재된 저자 전체의 영문 이름과 순서
- [ ] 각 저자의 ORCID 및 소속
- [ ] 교신저자 이메일
- [x] 코드 라이선스: MIT
- [x] 원고의 Data Availability 문구에 따라 참여자 데이터는 공유 불가로 명시

## GitHub 게시

- [ ] 이 폴더의 내용만 새 리포지토리에 업로드
- [ ] `.env`, 대화 로그, 설문 응답, DynamoDB 내보내기 파일을 올리지 않기
- [ ] 저자 정보로 `CITATION.cff` 작성
- [ ] 선택한 라이선스의 `LICENSE` 파일 추가
- [ ] GitHub 리포지토리를 Public으로 전환하기 전 전체 파일 재검토

## Zenodo DOI 발급

- [ ] Zenodo에 GitHub 계정으로 로그인
- [ ] GitHub 연동 화면에서 해당 리포지토리 활성화
- [ ] GitHub에서 `v1.0.0` Release 생성
- [ ] Zenodo 레코드의 제목, 저자 순서, ORCID, 초록, 키워드, 라이선스 확인
- [x] 버전 DOI 발급: `10.5281/zenodo.21359273`
- [x] 저장소의 Data Availability Statement에 DOI 삽입

## 편집부에 사용할 핵심 설명

참여자 응답 데이터는 공개하거나 요청 기반으로 제공하지 않고, 코드·프롬프트·에이전트 조건·실행 설정만 DOI가 있는 공개 저장소를 통해 제공합니다. 이는 제출 원고의 “The authors do not have permission to share data” 문구와 일치합니다.
