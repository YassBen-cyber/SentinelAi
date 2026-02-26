package com.example.demo.filter;

import com.example.demo.model.ApiLog;
import com.example.demo.repository.ApiLogRepository;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.LocalDateTime;

@Component
@RequiredArgsConstructor
public class LogFilter extends OncePerRequestFilter {

    private final ApiLogRepository apiLogRepository;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        long startTime = System.currentTimeMillis();

        // Wrap response to capture status code if needed, but for simplicity Spring
        // sets it on return
        try {
            filterChain.doFilter(request, response);
        } finally {
            long duration = System.currentTimeMillis() - startTime;

            ApiLog apiLog = new ApiLog();
            apiLog.setIpAddress(request.getRemoteAddr());
            apiLog.setTimestamp(LocalDateTime.now());
            apiLog.setEndpoint(request.getRequestURI());
            apiLog.setMethod(request.getMethod());
            apiLog.setStatusCode(response.getStatus());
            apiLog.setResponseTime(duration);
            apiLog.setUserAgent(request.getHeader("User-Agent"));

            // Simple payload suspension check for demo
            String queryString = request.getQueryString();
            if (queryString != null && (queryString.contains("script") || queryString.contains("select"))) {
                apiLog.setSuspectedPayload(queryString);
            }

            apiLogRepository.save(apiLog);
        }
    }
}
