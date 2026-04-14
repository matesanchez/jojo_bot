#!/bin/bash
echo "Starting Jojo Bot..."
echo ""

# Start backend
echo "Starting backend on :8000..."
cd src/backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ../..

# Wait for backend to be ready
sleep 3

# Start frontend
echo "Starting frontend on :3000..."
cd src/frontend
npm run dev &
FRONTEND_PID=$!
cd ../..

echo ""
echo "✅ Jojo Bot is running!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
