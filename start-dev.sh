#!/bin/bash

# Start backend
echo "Starting backend on http://localhost:8000..."
cd backend
python server.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
echo "Starting frontend on http://localhost:5173..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

echo ""
echo "Both servers running!"
echo "  - Frontend: http://localhost:5173"
echo "  - Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"

wait
