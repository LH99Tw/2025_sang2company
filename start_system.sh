#!/bin/bash

# 퀀트 금융 분석 시스템 실행 스크립트
# 백엔드(Flask)와 프론트엔드(React)를 동시에 실행합니다.

echo "🚀 퀀트 금융 분석 시스템을 시작합니다..."

# 현재 디렉토리 확인
if [ ! -f "start_system.sh" ]; then
    echo "❌ 프로젝트 루트 디렉토리에서 실행해주세요."
    exit 1
fi

# Python 가상환경 확인 및 생성
if [ ! -d "venv" ]; then
    echo "📦 Python 가상환경을 생성합니다..."
    python3 -m venv venv
fi

# 가상환경 활성화
echo "🔧 Python 가상환경을 활성화합니다..."
source venv/bin/activate

# Python 의존성 설치
if [ -f "backend/requirements.txt" ]; then
    echo "📦 Python 의존성을 설치합니다..."
    pip install -r backend/requirements.txt
fi

if [ -f "requirements.txt" ]; then
    echo "📦 추가 Python 의존성을 설치합니다..."
    pip install -r requirements.txt
fi

# Node.js 의존성 설치 (프론트엔드)
if [ -d "frontend" ]; then
    echo "📦 Node.js 의존성을 설치합니다..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    cd ..
fi

#백엔드 종료는 
#$ pkill -f "Flask"
#$ lsof -ti:5002 | xargs kill -9
# 백엔드 서버 시작 (백그라운드)
echo "🔧 Flask 백엔드 서버를 시작합니다..."
cd backend
python app.py &
BACKEND_PID=$!
cd ..

# 잠시 대기 (백엔드 서버 시작 대기)
sleep 3

# 프론트엔드 서버 시작
echo "🌐 React 프론트엔드 서버를 시작합니다..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ 시스템이 성공적으로 시작되었습니다!"
echo ""
echo "🌐 프론트엔드: http://localhost:3000"
echo "🔧 백엔드 API: http://localhost:5001"
echo ""
echo "시스템을 종료하려면 Ctrl+C를 누르세요."
echo ""

# 프로세스 종료 처리
cleanup() {
    echo ""
    echo "🛑 시스템을 종료합니다..."
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "✅ Flask 백엔드 서버가 종료되었습니다."
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "✅ React 프론트엔드 서버가 종료되었습니다."
    fi
    
    echo "👋 시스템이 완전히 종료되었습니다."
    exit 0
}

# Ctrl+C 시그널 처리
trap cleanup INT

# 무한 대기 (사용자가 Ctrl+C를 누를 때까지)
wait
