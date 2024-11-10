document.addEventListener('DOMContentLoaded', function () {
    const webcam = document.getElementById('webcam');
    const snapshot = document.getElementById('snapshot');
    const captureBtn = document.getElementById('capture-btn');
    const photoInput = document.getElementById('photo-input');

    if (navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(function (stream) {
                webcam.srcObject = stream;
            })
            .catch(function (error) {
                console.error("웹캠 접근에 실패했습니다.", error);
            });
    }

    captureBtn.addEventListener('click', function () {
        const context = snapshot.getContext('2d');
        snapshot.width = webcam.videoWidth;
        snapshot.height = webcam.videoHeight;
        context.drawImage(webcam, 0, 0);
        photoInput.value = snapshot.toDataURL('image/png');
    });
});
