 // 데이터 읽기 - 브라우저 콘솔에서 
fetch('/api/tasks')          // 서버에 /api/tasks 요청을 보낸다. (GET 요청) => 내 Task 목록을 가져온다. 
    .then(r => r.json())     // 응답을 JSON으로 변환한다. 받은 답은 읽을 수 있는 데이터로 바꾼다. 
    .then(console.log)          // 변환된 데이터를 브라우저 내장 콘솔(브라우저 개발자 도구 콘솔)에 출력한다.


// 다른 계정 데이터 수정 시도하기 - 404 warning 출력 기대
fetch('/api/tasks/19', {      //12번 Task 수정하기 - 브라우저 콘솔에서 'PATCH' 요청을 보낸다.
    method: 'PATCH',  //HTTP 요청 메서드 중 PATCH를 사용한다. (PATCH는 일부만 수정할 때 사용한다.)
    headers: {'Content-Type': 'application/json'}, // 요청헤더에 json 형식으로 데이터를 보내겠다고 명시한다.
    body: JSON.stringify({title: '수정해보기(콘솔변경)'}), // 요청 본문에 수정할 데이터를 JSON 문자열로 변환하여 담는다. (title을 '수정해보기(콘솔변경)'로 변경)
} ).then(r => console.log(r.status))     // 응답을 JSON으로 변환한다. 200번이면 성공, 401번이면 인증 실패, 404번이면 Task가 없음. 상태코드를 브라우저 콘솔에 출력한다.   