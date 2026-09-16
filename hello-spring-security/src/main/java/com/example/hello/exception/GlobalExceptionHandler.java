package com.example.hello.exception;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(InvalidCredentialsException.class)
    public ResponseEntity<Map<String, Object>> handleInvalidCredentials() {
        return build(401, "Invalid username or password");
    }

    private ResponseEntity<Map<String, Object>> build(int code, String message) {
        return ResponseEntity.status(HttpStatus.valueOf(code))
                .body(Map.of("code", code, "message", message));
    }
}
